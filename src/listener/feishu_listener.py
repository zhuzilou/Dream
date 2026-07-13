import os
import json
import re
import sqlite3
from datetime import datetime
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.ws import Client as WSClient
from loguru import logger
from scraper.akshare_client import get_stock_news, get_stock_hist, get_stock_current_price, resolve_stock_symbol, get_stock_audit_data, collect_board_observation_inputs
from analyst.llm_engine import Analyst
from analyst.risk_auditor import RiskAuditor
from strategist.trade_advisor import TradeAdvisor
from notifier.feishu import FeishuBot
from generator.card_renderer import render_markdown
from listener.intent_router import IntentType, route_intent
from memory.observation_memory import ObservationMemory
from memory.term_learning import TermLearningQueue
from scenarios.board_observation import BoardObservationService
from scenarios.stock_decision import StockDecisionService

# 动态获取数据库路径 (与 main.py 保持一致)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "scout.db")
if os.path.exists("/app/data/scout.db"):
    DB_PATH = "/app/data/scout.db"

class FeishuListener:
    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.analyst = Analyst()
        self.risk_auditor = RiskAuditor()
        self.advisor = TradeAdvisor()
        self.notifier = FeishuBot()
        self.processed_msg_ids = set() # 简单的内存去重

    def handle_message(self, data: P2ImMessageReceiveV1) -> None:
        """处理接收到的消息事件"""
        msg = data.event.message
        msg_id = msg.message_id
        
        if msg_id in self.processed_msg_ids:
            logger.info(f"Duplicate message ignored: {msg_id}")
            return
            
        self.processed_msg_ids.add(msg_id)
        if len(self.processed_msg_ids) > 1000:
            self.processed_msg_ids = set(list(self.processed_msg_ids)[-500:])

        content_str = msg.content
        chat_id = msg.chat_id
        
        try:
            content = json.loads(content_str)
            text = content.get("text", "")
            if not text:
                post_data = content.get("post", content)
                content_rows = []
                if isinstance(post_data, dict):
                    if "zh_cn" in post_data:
                        content_rows = post_data["zh_cn"].get("content", [])
                    elif "content" in post_data and isinstance(post_data["content"], list):
                        content_rows = post_data["content"]
                
                if content_rows:
                    try:
                        text_parts = []
                        for row in content_rows:
                            for element in row:
                                if element.get("tag") == "text":
                                    text_parts.append(element.get("text", ""))
                                elif element.get("tag") == "a":
                                    text_parts.append(element.get("text", ""))
                        text = "".join(text_parts)
                    except:
                        pass
            
            clean_text = re.sub(r'@[^\s]+\s?', '', text).strip()
            
            # V1.2 中回复审核已降级，不再读取父消息进入 RiskAuditor。
            parent_id = msg.parent_id or msg.root_id
            is_audit_command = any(k in clean_text for k in ["审核", "看看", "分析", "评价"])
            is_recommendation_request = any(k in clean_text for k in ["推荐", "选股", "买什么", "买哪", "哪支", "哪只"])
            
            logger.info(f"Received message from Feishu: {clean_text}")

            if parent_id and (not clean_text or clean_text in ["审核", "看看", "评价"]):
                self.handle_deprecated_audit(chat_id)
                return

            # 1. 意图分发
            intent = route_intent(clean_text)

            if intent.intent_type == IntentType.HELP:
                self.send_help(chat_id)
                return

            if intent.intent_type == IntentType.TERM_LEARNING:
                self.handle_term_learning(chat_id, clean_text)
                return

            if intent.intent_type == IntentType.OBSERVATION_REVIEW:
                self.handle_observation_memory(chat_id, clean_text)
                return

            if intent.intent_type == IntentType.DEPRECATED_AUDIT:
                self.handle_deprecated_audit(chat_id)
                return

            if intent.intent_type == IntentType.SCENARIO_BOARD_OBSERVATION:
                self.handle_board_observation(chat_id, clean_text)
                return

            if intent.intent_type == IntentType.SCENARIO_STOCK_DECISION:
                res = self._resolve_stock_from_text(clean_text)
                if res:
                    self.handle_stock_decision(chat_id, res['symbol'], res['name'], clean_text)
                    return
                self.notifier.send_text_message(
                    chat_id,
                    "⚠️ 我没能识别出要分析的股票，请直接输入股票名称或代码。示例：上海电力最近一直跌，可以买吗？ / 分析 600021",
                    receive_id_type="chat_id"
                )
                return
            
            # A. 帮助指令
            if clean_text in ["帮助", "help", "帮助", "菜单", "指令"]:
                self.send_help(chat_id)
                return

            # B. 监控指令
            if clean_text.startswith("监控") or "加入观察池" in clean_text:
                query = re.sub(r'将|加入观察池|监控|添加', '', clean_text).strip()
                if query:
                    self.handle_add_to_watchlist(chat_id, query)
                else:
                    self.notifier.send_text_message(chat_id, "⚠️ 请输入要监控的股票名称或代码。示例：监控 纳百川", receive_id_type="chat_id")
                return

            # C. 买入指令
            elif clean_text.startswith("买入"):
                parts = re.split(r'\s+', clean_text)
                if len(parts) >= 3:
                    query = parts[1]
                    try:
                        price = float(parts[2])
                        qty = float(parts[3]) if len(parts) >= 4 else 0
                        self.handle_add_to_positions(chat_id, query, price, qty)
                    except ValueError:
                        self.notifier.send_text_message(chat_id, "⚠️ 价格或数量格式错误。示例：买入 纳百川 105.5 500", receive_id_type="chat_id")
                else:
                    self.notifier.send_text_message(chat_id, "⚠️ 请提供股票和买入价格。示例：买入 纳百川 105.5 500", receive_id_type="chat_id")
                return

            # D. 卖出/移除指令
            elif clean_text.startswith("卖出") or clean_text.startswith("移除") or clean_text.startswith("删"):
                parts = re.split(r'\s+', clean_text)
                if len(parts) >= 2:
                    query = parts[1]
                    qty = parts[2] if len(parts) >= 3 else "全部"
                    self.handle_remove(chat_id, query, qty)
                else:
                    self.notifier.send_text_message(chat_id, "⚠️ 请提供股票名称或代码。示例：卖出 纳百川 200", receive_id_type="chat_id")
                return

            # E. 池子列表
            elif clean_text in ["池子", "列表", "监控池", "持仓", "清单", "仓位"]:
                self.list_pools(chat_id)
                return

            # F. 持仓分析 (新)
            elif clean_text in ["持仓分析", "分析持仓", "体检", "诊断"]:
                self.handle_portfolio_analysis(chat_id)
                return

            # G. 选股推荐请求
            elif is_recommendation_request:
                stock_res = self._resolve_stock_from_text(clean_text)
                if stock_res:
                    self.process_instant_analysis(chat_id, stock_res['symbol'], stock_res['name'])
                else:
                    self.handle_stock_recommendation(chat_id)
                return

            # H. 股票分析 (即时请求)
            elif re.search(r'\d{6}', clean_text) or (is_audit_command and clean_text):
                res = self._resolve_stock_from_text(clean_text)
                if res:
                    self.handle_stock_decision(chat_id, res['symbol'], res['name'], clean_text)
                    return
                self.notifier.send_text_message(
                    chat_id,
                    "⚠️ 我没能识别出要分析的股票，请直接输入股票名称或代码。示例：分析 上海电力 / 分析 600021",
                    receive_id_type="chat_id"
                )
                return

            # I. 基础交互
            elif any(k in clean_text for k in ["你好", "谁", "助", "Hi", "Hello"]):
                self.send_help(chat_id)
            else:
                response = self.analyst.chat(clean_text)
                self.notifier.send_interactive_message(chat_id, "🤖 Frank 答复", response, receive_id_type="chat_id")
                
        except Exception as e:
            logger.error(f"Error handling Feishu message: {e}")

    # --- 核心业务逻辑 ---

    def _resolve_stock_from_text(self, text):
        """从自然语言文本中提取并解析股票。"""
        match = re.search(r'\d{6}', text)
        if match:
            return resolve_stock_symbol(match.group())

        query = re.sub(r'分析|看看|研报|评价|推荐|选股', '', text).strip()
        query = re.sub(r'帮我|麻烦|请|看一下|看下|一下|下', '', query)
        query = re.sub(r'走势|趋势|情况|是否|有没有|有|合适|适合|买入点|买点|买入|可以|能不能|现在|近期|怎么样|如何|吗|呢', '', query)
        query = re.sub(r'[\s，,。！？?、；;：:]+', '', query)
        if query:
            res = resolve_stock_symbol(query)
            if res:
                return res

        scan_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
        stop_words = set(["分析", "看看", "走势", "情况", "是否", "合适", "适合", "买入", "推荐", "选股"])
        for length in range(6, 1, -1):
            for i in range(0, max(len(scan_text) - length + 1, 0)):
                word = scan_text[i:i + length]
                if word in stop_words:
                    continue
                res = resolve_stock_symbol(word)
                if res and (res.get('name') == word or word in res.get('name', '')):
                    return res
        return None

    def _format_decision_support(self, plan):
        """格式化交易辅助决策信息。"""
        trigger_conditions = plan.get("trigger_conditions") or []
        invalidation_conditions = plan.get("invalidation_conditions") or []
        review_plan = plan.get("review_plan") or []

        def format_items(items):
            return "\n".join([f"- {item}" for item in items]) if items else "- 暂无明确条件"

        return (
            f"🧭 **决策置信度**: {plan.get('confidence', '未评估')}\n"
            f"📦 **仓位建议**: {plan.get('position_advice', '暂无')}\n\n"
            f"✅ **触发条件**:\n{format_items(trigger_conditions)}\n\n"
            f"❌ **失效条件**:\n{format_items(invalidation_conditions)}\n\n"
            f"🗓️ **复盘计划**:\n{format_items(review_plan)}"
        )

    def handle_stock_recommendation(self, chat_id):
        """处理没有明确股票标的的选股请求。"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT symbol, name FROM watchlist WHERE status = "active"')
            watchlist = cursor.fetchall()
            cursor.execute('SELECT symbol, name, quantity, entry_price FROM positions')
            positions = cursor.fetchall()
        finally:
            conn.close()

        candidates = []
        for symbol, name in watchlist[:5]:
            candidates.append(f"- 观察池：{name or symbol} ({symbol})")
        for symbol, name, qty, price in positions[:5]:
            candidates.append(f"- 持仓池：{name or symbol} ({symbol}) | {qty or 0}股 | 成本 {price}")

        candidate_text = "\n".join(candidates) if candidates else "- 当前观察池和持仓池为空，请先用 `监控 股票名称` 建立候选池。"
        md = (
            "我可以帮你做选股，但第一版会优先从 **观察池** 和 **持仓池** 里筛选，"
            "避免在没有范围和数据约束时给出拍脑袋推荐。\n\n"
            "**当前候选范围**：\n"
            f"{candidate_text}\n\n"
            "**建议用法**：\n"
            "- `分析 上海电力`：分析指定股票走势和买点\n"
            "- `监控 上海电力`：加入观察池，后续让 Frank 持续跟踪\n"
            "- `持仓分析`：从已有持仓里找风险和机会\n\n"
            "后续可以继续升级为全市场选股，但需要先定义行业、风险偏好、持仓周期和最大回撤。"
        )
        self.notifier.send_interactive_message(chat_id, "🔎 Frank 选股助手", md, receive_id_type="chat_id")

    def handle_deprecated_audit(self, chat_id):
        md = (
            "这个“审核”入口在 V1.2 已降级，不再作为主流程。\n\n"
            "原因是股票价格、成交量和涨跌幅变化很快，直接审判一段内容容易把时效偏差误判成错误。\n\n"
            "你可以改成问一个具体股票或板块，例如：\n"
            "- `上海电力最近一直跌，可以买入吗？`\n"
            "- `最近有哪些板块值得关注？`\n\n"
            "Frank 会按真实行情、观察条件和失效条件辅助你判断，最终决策仍由你完成。"
        )
        self.notifier.send_interactive_message(chat_id, "Frank 审核入口已降级", md, receive_id_type="chat_id")

    def handle_stock_decision(self, chat_id, symbol, name, raw_question):
        hist_df = get_stock_hist(symbol)
        price_res = get_stock_current_price(symbol)
        service = StockDecisionService()
        result = service.build_decision(
            raw_question=raw_question,
            stock={"symbol": symbol, "name": name},
            price_data=price_res,
            hist_df=hist_df,
            news_summary="新闻只作为辅助信息，本次主要依据行情、均线、支撑压力和成交量。"
        )
        self.notifier.send_interactive_message(chat_id, result.card.title, render_markdown(result.card), receive_id_type="chat_id")

    def handle_board_observation(self, chat_id, raw_question):
        memory = ObservationMemory(DB_PATH)
        memory.init_schema()
        service = BoardObservationService(memory=memory)
        now = datetime.now()
        is_intraday = now.hour < 15
        boards = collect_board_observation_inputs(max_boards=3)
        if not boards:
            result = service.build_unavailable(
                reason="AkShare 板块数据源暂不可用或返回空结果。",
                data_timestamp=now,
                is_intraday=is_intraday
            )
        else:
            result = service.build_observation(
                market_summary="当前市场方向以板块资金、涨跌幅、成交活跃度和可持续性综合判断。",
                boards=boards,
                data_timestamp=now,
                is_intraday=is_intraday
            )
        self.notifier.send_interactive_message(chat_id, result.card.title, render_markdown(result.card), receive_id_type="chat_id")

    def handle_term_learning(self, chat_id, raw_text):
        queue = TermLearningQueue(DB_PATH)
        queue.init_schema()
        compact = re.sub(r"\s+", " ", raw_text).strip()
        if compact.startswith("记录术语"):
            parts = compact.split(" ")
            term = parts[1] if len(parts) >= 2 else ""
            scene = parts[2] if len(parts) >= 3 else ""
            if not term:
                self.notifier.send_text_message(chat_id, "⚠️ 请提供术语。示例：记录术语 放量修复 场景7.1", receive_id_type="chat_id")
                return
            queue.record_term(term, raw_text, related_scene=scene)
            md = f"已记录待补充术语：**{term}**" + (f"\n\n关联场景：{scene}" if scene else "")
        elif compact == "待补充术语":
            rows = queue.list_pending()
            md = "\n".join([f"- {row['term']} | {row['related_scene']} | {row['status']}" for row in rows]) or "暂无待补充术语。"
        elif compact == "导出术语记录":
            md = queue.export_records()
        else:
            rows = queue.list_recent()
            md = "\n".join([f"- {row['term']} | {row['related_scene']} | {row['status']}" for row in rows]) or "暂无术语记录。"
        self.notifier.send_interactive_message(chat_id, "Frank 术语学习记录", md, receive_id_type="chat_id")

    def handle_observation_memory(self, chat_id, raw_text):
        memory = ObservationMemory(DB_PATH)
        memory.init_schema()
        compact = re.sub(r"\s+", "", raw_text or "")
        match = re.match(r"复盘观察池(\d+)$", compact)
        if match:
            self.handle_observation_review(chat_id, memory, int(match.group(1)))
            return

        runs = memory.list_recent_runs()
        if not runs:
            md = "暂无 Observation Memory。你可以先问：`最近有哪些板块值得关注？`"
        else:
            lines = []
            for run in runs:
                lines.append(f"- #{run['id']} | {run['trade_date']} | {run['status']} | {run['market_summary']}")
            md = "\n".join(lines)
        self.notifier.send_interactive_message(chat_id, "Frank Observation Memory", md, receive_id_type="chat_id")

    def handle_observation_review(self, chat_id, memory, run_id):
        run = memory.get_run(run_id)
        if not run:
            self.notifier.send_interactive_message(chat_id, "Frank Observation Review", f"未找到观察池 #{run_id}。", receive_id_type="chat_id")
            return

        stocks = memory.list_stocks(run_id)
        if not stocks:
            md = (
                f"观察池 #{run_id} 没有可复盘候选股。\n\n"
                "复盘用于学习，不证明当初推荐一定正确；如果当时数据源失败，应该重新生成观察池。"
            )
            self.notifier.send_interactive_message(chat_id, "Frank Observation Review", md, receive_id_type="chat_id")
            return

        lines = [
            f"观察池 #{run_id} 复盘",
            "",
            "复盘用于学习，不证明当初推荐一定正确。",
            "重点看条件是否成立、哪些条件失效，以及下一次观察应更谨慎的地方。",
            ""
        ]
        for stock in stocks:
            hist_df = get_stock_hist(stock["symbol"])
            rows = self._hist_rows(hist_df)
            condition_results = self._review_condition_results(rows)
            price_snapshot = self._review_price_snapshot(rows)
            conclusion = self._review_conclusion(condition_results)
            lesson = "下一次仍要先进入场景一确认触发条件和失效条件，不能把观察池当买入名单。"
            memory.add_review(
                stock["id"], datetime.now().strftime("%Y-%m-%d"),
                price_snapshot, condition_results, conclusion, lesson
            )
            lines.extend([
                f"- {stock['name']}({stock['symbol']})",
                f"  - 条件是否成立：{condition_results['summary']}",
                f"  - 复盘结论：{conclusion}",
                f"  - 学习要点：{lesson}"
            ])

        self.notifier.send_interactive_message(chat_id, "Frank Observation Review", "\n".join(lines), receive_id_type="chat_id")

    def _hist_rows(self, hist_df):
        if hist_df is None:
            return []
        if isinstance(hist_df, list):
            return hist_df
        if hasattr(hist_df, "to_dict"):
            try:
                return hist_df.to_dict("records")
            except TypeError:
                return []
        return []

    def _review_condition_results(self, rows):
        if not rows:
            return {
                "summary": "行情数据不足，无法判断观察条件是否成立。",
                "has_follow_through": False,
                "volume_improved": False
            }
        closes = [float(row.get("close", row.get("收盘", 0)) or 0) for row in rows]
        volumes = [float(row.get("volume", row.get("成交量", 0)) or 0) for row in rows]
        first_close = closes[0] if closes else 0
        last_close = closes[-1] if closes else 0
        has_follow_through = last_close >= first_close
        volume_improved = len(volumes) >= 2 and volumes[-1] >= volumes[0]
        summary = "价格没有跌回观察起点" if has_follow_through else "价格跌回观察起点下方"
        summary += "，成交量有配合。" if volume_improved else "，成交量配合不足。"
        return {
            "summary": summary,
            "has_follow_through": has_follow_through,
            "volume_improved": volume_improved
        }

    def _review_price_snapshot(self, rows):
        if not rows:
            return {"data_available": False}
        first = rows[0]
        last = rows[-1]
        return {
            "data_available": True,
            "start_close": first.get("close", first.get("收盘")),
            "latest_close": last.get("close", last.get("收盘")),
            "latest_date": last.get("date", last.get("日期"))
        }

    def _review_conclusion(self, condition_results):
        if not condition_results.get("has_follow_through"):
            return "暂未看到观察条件成立，更适合继续等待确认。"
        if condition_results.get("volume_improved"):
            return "观察条件部分成立，但仍需进入场景一确认具体触发条件。"
        return "价格表现有所修复，但成交量不足，仍不适合直接视为买点。"

    def send_help(self, chat_id):
        help_md = (
            "我是 **Frank Gemini**，你的 A 股投研陪练，不替你做买卖决定。\n\n"
            "🎯 **V1.2 主入口**：\n"
            "1. **个股能不能买**：`上海电力最近一直跌，可以买吗？`\n"
            "2. **板块观察池**：`最近有哪些板块值得关注？` / `收盘后帮我看方向`\n"
            "3. **查看观察池**：`查看观察池` / `最近观察池`\n"
            "4. **复盘观察池**：`复盘观察池 1`\n"
            "5. **记录术语**：`记录术语 放量修复 场景7.1` / `导出术语记录`\n\n"
            "🧭 **历史功能，暂保留**：\n"
            "- `监控 [名称/代码]`：手动 watchlist。\n"
            "- `买入/卖出 [名称/代码] ...`：持仓记录。\n"
            "- `池子` / `持仓分析`：查看历史 watchlist 与 positions。\n\n"
            "所有输出只做条件观察和风险提示，最终决策由你完成。"
        )
        self.notifier.send_interactive_message(chat_id, "📖 Frank Gemini 使用指南", help_md, receive_id_type="chat_id")

    def handle_audit(self, chat_id, target_content):
        # 1. 尝试提取股票信息以获取实时上下文 (滑动窗口 + 6位代码)
        found_stocks = []
        seen_symbols = set()
        
        # A. 优先匹配 6 位数字代码
        potential_codes = re.findall(r'\d{6}', target_content)
        for code in potential_codes:
            res = resolve_stock_symbol(code)
            if res and res['symbol'] not in seen_symbols:
                found_stocks.append(res)
                seen_symbols.add(res['symbol'])
            if len(found_stocks) >= 2: break
            
        # B. 滑动窗口匹配中文名 (2-4位汉字)
        if len(found_stocks) < 2:
            scan_text = target_content[:500] 
            candidates = []
            for i in range(len(scan_text)):
                for length in range(2, 5):
                    if i + length <= len(scan_text):
                        word = scan_text[i:i+length]
                        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', word):
                            candidates.append(word)
            
            for word in candidates:
                if word in ["审核", "分析", "投资", "建议", "策略", "评价", "现在", "价格", "适合", "买入", "卖出"]: continue
                res = resolve_stock_symbol(word)
                if res and res['symbol'] not in seen_symbols:
                    if res['name'] == word or (len(word) >= 3 and word in res['name']):
                        found_stocks.append(res)
                        seen_symbols.add(res['symbol'])
                if len(found_stocks) >= 2: break
        
        # 2. 获取增强版实时行情数据作为审计参考
        market_context = ""
        if found_stocks:
            analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ctx_lines = [
                "\n[Frank 分析时点行情参考]:",
                f"- 分析时间: {analysis_time}",
                "- 说明: 以下行情仅代表 Frank 当前分析时点。若与原消息存在差异，优先判断为市场快速变化造成的时效偏差，不得归咎于数据提供者。"
            ]
            for s in found_stocks:
                audit_data = get_stock_audit_data(s['symbol'])
                if audit_data["price"] > 0:
                    freshness_note = "延时/降级数据，仅作辅助参考" if audit_data.get("is_fallback") else "实时行情参考"
                    ctx_lines.append(
                        f"- {s['name']} ({s['symbol']}): "
                        f"现价 {audit_data['price']} 元, "
                        f"今日涨跌幅 {audit_data['change_pct']}%, "
                        f"换手率 {audit_data['turnover']}%, "
                        f"5日累计涨跌幅 {audit_data['five_day_change']}%, "
                        f"数据状态: {freshness_note}"
                    )
            market_context = "\n".join(ctx_lines)

        # 3. 调用 RiskAuditor 执行审计
        logger.info(f"Triggering RiskAuditor audit for {len(found_stocks)} stocks context.")
        response = self.risk_auditor.audit(target_content, market_context)
        
        # 冗余清理：防止 LLM 忽略指令产生 # 标题
        clean_response = re.sub(r'^#+\s+(.*)$', r'**\1**', response, flags=re.M)
        
        md = (
            f"🔍 **审计对象回顾**：\n> {target_content[:100]}...\n\n"
            f"⚖️ **Frank 审计报告**：\n{clean_response}"
        )
        self.notifier.send_interactive_message(chat_id, "⚖️ 投资内容审计报告", md, receive_id_type="chat_id")

    def handle_add_to_watchlist(self, chat_id, query):
        res = resolve_stock_symbol(query)
        if not res:
            self.notifier.send_text_message(chat_id, f"⚠️ 未能找到股票: {query}", receive_id_type="chat_id")
            return
        
        symbol, name = res['symbol'], res['name']
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT OR REPLACE INTO watchlist (symbol, name, added_at) VALUES (?, ?, datetime("now", "localtime"))', (symbol, name))
            conn.commit()
            self.notifier.send_interactive_message(chat_id, "✅ 监控已开启", f"已将 **{name} ({symbol})** 加入观察池。\nScout 侦察员将在下次定时任务中为您汇报最新动向。", receive_id_type="chat_id")
        except Exception as e:
            logger.error(f"DB Error: {e}")
        finally:
            conn.close()

    def handle_add_to_positions(self, chat_id, query, price, qty=0):
        res = resolve_stock_symbol(query)
        if not res:
            self.notifier.send_text_message(chat_id, f"⚠️ 未能找到股票: {query}", receive_id_type="chat_id")
            return
        
        symbol, name = res['symbol'], res['name']
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # 1. 检查是否已有持仓
            cursor.execute('SELECT quantity, entry_price FROM positions WHERE symbol = ?', (symbol,))
            row = cursor.fetchone()
            
            new_qty = qty
            new_price = price
            action_desc = "建仓"
            
            if row:
                old_qty, old_price = row[0] or 0, row[1]
                if old_qty > 0 and qty > 0:
                    # 摊薄成本计算
                    new_qty = old_qty + qty
                    new_price = round((old_price * old_qty + price * qty) / new_qty, 3)
                    action_desc = "加仓"
                elif qty == 0:
                    new_qty = old_qty
            
            sl = round(new_price * 0.95, 2)
            tp = round(new_price * 1.15, 2)
            
            cursor.execute('''
                INSERT OR REPLACE INTO positions (symbol, name, entry_price, quantity, entry_date, stop_loss, take_profit)
                VALUES (?, ?, ?, ?, datetime("now", "localtime"), ?, ?)
            ''', (symbol, name, new_price, new_qty, sl, tp))
            
            # 2. 记录到交易日记
            cursor.execute('''
                INSERT INTO trade_journal (symbol, name, action, price, quantity, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, name, "BUY", price, qty, f"Feishu指令{action_desc}"))
            
            cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
            conn.commit()
            
            msg = (
                f"✅ **{name} ({symbol})** {action_desc}登记成功：\n"
                f"- 成交价格: **{price}** 元\n"
                f"- 持仓数量: **{new_qty}** 股\n"
                f"- 平均成本: **{new_price}** 元\n"
                f"- Frank 建议止损: **{sl}** 元\n\n"
                "🛡️ 高频风险监控已同步更新。"
            )
            self.notifier.send_interactive_message(chat_id, f"💰 {action_desc}档案已更新", msg, receive_id_type="chat_id")
        except Exception as e:
            logger.error(f"DB Error: {e}")
            self.notifier.send_text_message(chat_id, f"❌ 数据库操作失败: {e}", receive_id_type="chat_id")
        finally:
            conn.close()

    def handle_remove(self, chat_id, query, qty_str="全部"):
        symbol = query
        if not re.match(r'^\d{6}$', query):
            res = resolve_stock_symbol(query)
            if res: symbol = res['symbol']
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # 获取当前持仓和名称
            cursor.execute('SELECT name, quantity, entry_price FROM positions WHERE symbol = ?', (symbol,))
            row = cursor.fetchone()
            if not row:
                # 仅在观察池中，直接移除
                cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
                conn.commit()
                self.notifier.send_text_message(chat_id, f"🗑️ 已移除对 {symbol} 的监控。", receive_id_type="chat_id")
                return

            name, old_qty, price = row[0], row[1] or 0, row[2]
            sell_qty = 0
            is_full_sell = False
            
            if qty_str == "全部":
                is_full_sell = True
                sell_qty = old_qty
            else:
                try:
                    sell_qty = float(qty_str)
                    if sell_qty >= old_qty:
                        is_full_sell = True
                        sell_qty = old_qty
                except:
                    is_full_sell = True
                    sell_qty = old_qty

            if is_full_sell:
                cursor.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
                msg = f"🚫 已清仓并移除 **{name} ({symbol})**。"
            else:
                new_qty = old_qty - sell_qty
                cursor.execute('UPDATE positions SET quantity = ? WHERE symbol = ?', (new_qty, symbol))
                msg = f"📉 **{name} ({symbol})** 已减仓 {sell_qty} 股，剩余 {new_qty} 股。"

            # 记录交易日记
            cursor.execute('''
                INSERT INTO trade_journal (symbol, name, action, price, quantity, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, name, "SELL", 0, sell_qty, "Feishu指令卖出"))
            
            conn.commit()
            self.notifier.send_text_message(chat_id, msg, receive_id_type="chat_id")
        except Exception as e:
            logger.error(f"DB Error: {e}")
        finally:
            conn.close()

    def list_pools(self, chat_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT symbol, name FROM watchlist')
            watchlist = [f"{row[1] or '未知'}({row[0]})" for row in cursor.fetchall()]
            
            cursor.execute('SELECT symbol, name, entry_price, quantity, stop_loss FROM positions')
            positions = []
            for row in cursor.fetchall():
                name, symbol, price, qty, sl = row[1] or '未知', row[0], row[2], row[3] or 0, row[4]
                positions.append(f"**{name}** ({symbol}) | {qty}股 | 成本:{price} | 止损:{sl}")
            
            md = "**👀 观察池 (Watchlist)**\n"
            md += (", ".join(watchlist) if watchlist else "*暂无股票*") + "\n\n"
            md += "--- \n"
            md += "**🛡️ 持仓池 (Holdings)**\n"
            md += ("\n".join([f"- {p}" for p in positions]) if positions else "*暂无持仓*")
            
            self.notifier.send_interactive_message(chat_id, "📋 Frank 的监控清单", md, receive_id_type="chat_id")
        finally:
            conn.close()

    def handle_portfolio_analysis(self, chat_id):
        """对所有持仓进行体检"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT symbol, name, quantity, entry_price FROM positions')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.notifier.send_text_message(chat_id, "🛡️ 您目前没有任何持仓。可以尝试输入 `分析 股票名称` 来寻找机会。", receive_id_type="chat_id")
            return

        self.notifier.send_text_message(chat_id, f"🔍 正在对 {len(rows)} 只持仓股票进行深度体检，请稍候...", receive_id_type="chat_id")
        
        reports = []
        for symbol, name, qty, price in rows:
            # 复用即时分析的逻辑片段，但合并输出
            news_df = get_stock_news(symbol)
            hist_df = get_stock_hist(symbol)
            price_res = get_stock_current_price(symbol)
            
            title = "无近期新闻"
            content = ""
            if not news_df.empty:
                title = str(news_df.iloc[0].get('新闻标题', ''))
                content = str(news_df.iloc[0].get('新闻内容', ''))
            
            ai_analysis = self.analyst.analyze_news(title, content, symbol=symbol)
            current_pos = {"quantity": qty, "entry_price": price}
            plan = self.advisor.generate_plan(symbol, price_res, hist_df, ai_analysis, current_pos=current_pos)
            
            if plan:
                decision_support = self._format_decision_support(plan)
                reports.append(
                    f"### 📌 {name or symbol} ({qty}股)\n"
                    f"- **建议**: **{plan['action']}**\n"
                    f"- **理由**: {plan['reason']}\n"
                    f"{decision_support}\n"
                )
        
        full_md = "\n".join(reports)
        self.notifier.send_interactive_message(chat_id, "📊 Frank 持仓深度体检报告", full_md, receive_id_type="chat_id")

    def _get_position(self, symbol):
        """获取本地持仓数据"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT quantity, entry_price FROM positions WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"quantity": row[0], "entry_price": row[1]}
        return None

    def process_instant_analysis(self, chat_id, symbol, name=""):
        """执行即时分析逻辑"""
        self.notifier.send_text_message(chat_id, f"🔍 收到指令！正在为 {name or symbol} 搜集资讯并建模...", receive_id_type="chat_id")
        
        news_df = get_stock_news(symbol)
        hist_df = get_stock_hist(symbol)
        price_res = get_stock_current_price(symbol)
        current_price = price_res["price"]
        current_pos = self._get_position(symbol)
        
        if news_df is None or news_df.empty:
            self.notifier.send_text_message(chat_id, f"⚠️ 暂时没有搜寻到关于 {symbol} 的近期资讯。", receive_id_type="chat_id")
            return

        title = str(news_df.iloc[0].get('新闻标题', news_df.iloc[0].get('title', '')))
        content = str(news_df.iloc[0].get('新闻内容', news_df.iloc[0].get('content', '')))
        ai_analysis = self.analyst.analyze_news(title, content, symbol=symbol)
        
        if not ai_analysis:
            self.notifier.send_text_message(chat_id, "❌ AI 分析过程出错，请检查 API 状态。", receive_id_type="chat_id")
            return

        plan = self.advisor.generate_plan(symbol, price_res, hist_df, ai_analysis, current_pos=current_pos)
        
        if plan:
            action = plan['action']
            emoji = "🎯" if "买入" in action else ("🛡️" if "减仓" in action else "💤")
            msg_title = f"{emoji} | {name or symbol} 综合建议"
            decision_support = self._format_decision_support(plan)
            
            warning = " (⚠️ 延时数据)" if price_res.get("is_fallback") else ""
            md = (
                f"💰 **当前价**: {current_price} 元{warning}\n"
                f"📈 **技术趋势**: {plan['trend']}\n\n"
                f"💡 **AI 核心结论**:\n> {ai_analysis.get('summary', '无')}\n\n"
                f"✅ **建议操作**: **{action}**\n"
                f"📊 **参考位**: 买入 {plan['buy_price'] or '--'} | 止损 {plan['stop_loss'] or '--'} | 止盈 {plan['take_profit'] or '--'}\n\n"
                f"📝 **逻辑分析**:\n{plan['reason']}"
                f"\n\n{decision_support}"
            )
            self.notifier.send_interactive_message(chat_id, msg_title, md, receive_id_type="chat_id")
        else:
            self.notifier.send_text_message(chat_id, "❌ 策略建模失败。", receive_id_type="chat_id")

    def start(self):
        """启动 WebSocket 客户端"""
        event_handler = lark.EventDispatcherHandler.builder("", "") \
            .register_p2_im_message_receive_v1(self.handle_message) \
            .build()

        client = WSClient(self.app_id, self.app_secret, event_handler=event_handler, log_level=lark.LogLevel.INFO)
        logger.info("Frank Gemini WebSocket listener starting...")
        client.start()
