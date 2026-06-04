import os
import json
import re
import sqlite3
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.ws import Client as WSClient
from loguru import logger
from scraper.akshare_client import get_stock_news, get_stock_hist, get_stock_current_price, resolve_stock_symbol, get_stock_audit_data
from analyst.llm_engine import Analyst
from analyst.risk_auditor import RiskAuditor
from strategist.trade_advisor import TradeAdvisor
from notifier.feishu import FeishuBot

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
            
            # 检测是否是“回复”消息（即审核模式）
            parent_id = msg.parent_id or msg.root_id
            audited_content = ""
            is_audit_command = any(k in clean_text for k in ["审核", "看看", "分析", "评价"])
            
            if parent_id and (is_audit_command or not clean_text):
                logger.info(f"Audit mode triggered for parent message: {parent_id}")
                audited_content = self.notifier.get_message_content(parent_id)
            
            logger.info(f"Received message from Feishu: {clean_text}")

            # 1. 意图分发
            
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
                match = re.search(r'买入\s+([^\s]+)\s+([\d\.]+)', clean_text)
                if match:
                    query, price = match.groups()
                    self.handle_add_to_positions(chat_id, query, float(price))
                else:
                    self.notifier.send_text_message(chat_id, "⚠️ 请提供股票和买入价格。示例：买入 纳百川 105.5", receive_id_type="chat_id")
                return

            # D. 卖出/移除指令
            elif clean_text.startswith("卖出") or clean_text.startswith("移除") or clean_text.startswith("删"):
                query = re.sub(r'卖出|移除|删', '', clean_text).strip()
                if query:
                    self.handle_remove(chat_id, query)
                else:
                    self.notifier.send_text_message(chat_id, "⚠️ 请提供股票名称或代码。示例：卖出 纳百川", receive_id_type="chat_id")
                return

            # E. 池子列表
            elif clean_text in ["池子", "列表", "监控池", "持仓", "清单"]:
                self.list_pools(chat_id)
                return

            # F. 审核模式 (通过回复触发)
            elif audited_content:
                self.handle_audit(chat_id, audited_content)
                return

            # G. 股票分析 (即时请求)
            elif re.search(r'\d{6}', clean_text) or (is_audit_command and clean_text):
                query = re.sub(r'分析|看看|研报|评价', '', clean_text).strip()
                if query:
                    res = resolve_stock_symbol(query)
                    if res:
                        self.process_instant_analysis(chat_id, res['symbol'], res['name'])
                        return
                
                # 如果没解析出来且有 6 位代码，按代码试
                match = re.search(r'\d{6}', clean_text)
                if match:
                    self.process_instant_analysis(chat_id, match.group())
                    return

            # H. 基础交互
            elif any(k in clean_text for k in ["你好", "谁", "助", "Hi", "Hello"]):
                self.send_help(chat_id)
            else:
                response = self.analyst.chat(clean_text)
                self.notifier.send_interactive_message(chat_id, "🤖 Frank 答复", response, receive_id_type="chat_id")
                
        except Exception as e:
            logger.error(f"Error handling Feishu message: {e}")

    # --- 核心业务逻辑 ---

    def send_help(self, chat_id):
        help_md = (
            "我是 **Frank Gemini** 🤖，您的 A 股 AI 投资助理。\n\n"
            "🎯 **核心指令**：\n"
            "--- \n"
            "1️⃣ **监控 [名称/代码]**\n"
            "> 加入观察池，开启每日 3 次的定时资讯抓取与 AI 情绪分析。\n"
            "> *示例：监控 纳百川*\n\n"
            "2️⃣ **买入 [名称/代码] [成本]**\n"
            "> 转入持仓管理，Frank 将建议止损位并开启高频风险盯盘。\n"
            "> *示例：买入 301667 105.2*\n\n"
            "3️⃣ **分析 [名称/代码]**\n"
            "> 即时进行“技术面+资讯”深度建模，生成研报卡片。\n"
            "> *示例：分析 贵州茅台*\n\n"
            "4️⃣ **池子**\n"
            "> 查看当前的【观察池】和【持仓池】清单。\n\n"
            "5️⃣ **卖出 [名称/代码]**\n"
            "> 从所有监控清单中彻底移除该股。\n\n"
            "💡 **进阶玩法**：直接回复某条资讯消息并输入“**审核**”，我会为您深入复核其逻辑。"
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
            ctx_lines = ["\n[当前市场实时数据参考]:"]
            for s in found_stocks:
                audit_data = get_stock_audit_data(s['symbol'])
                if audit_data["price"] > 0:
                    ctx_lines.append(
                        f"- {s['name']} ({s['symbol']}): "
                        f"现价 {audit_data['price']} 元, "
                        f"今日涨跌幅 {audit_data['change_pct']}%, "
                        f"换手率 {audit_data['turnover']}%, "
                        f"5日累计涨跌幅 {audit_data['five_day_change']}%"
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

    def handle_add_to_positions(self, chat_id, query, price):
        res = resolve_stock_symbol(query)
        if not res:
            self.notifier.send_text_message(chat_id, f"⚠️ 未能找到股票: {query}", receive_id_type="chat_id")
            return
        
        symbol, name = res['symbol'], res['name']
        sl = round(price * 0.95, 2)
        tp = round(price * 1.15, 2)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO positions (symbol, name, entry_price, entry_date, stop_loss, take_profit)
                VALUES (?, ?, ?, datetime("now", "localtime"), ?, ?)
            ''', (symbol, name, price, sl, tp))
            cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
            conn.commit()
            
            msg = (
                f"已为 **{name} ({symbol})** 建立仓位档案：\n"
                f"- 买入成本: **{price}** 元\n"
                f"- Frank 建议止损: **{sl}** 元\n"
                f"- Frank 建议止盈: **{tp}** 元\n\n"
                "🛡️ 系统已开启高频风险监控，一旦触发参考位或基本面反转将立即告警。"
            )
            self.notifier.send_interactive_message(chat_id, "💰 持仓档案已建立", msg, receive_id_type="chat_id")
        except Exception as e:
            logger.error(f"DB Error: {e}")
        finally:
            conn.close()

    def handle_remove(self, chat_id, query):
        symbol = query
        if not re.match(r'^\d{6}$', query):
            res = resolve_stock_symbol(query)
            if res: symbol = res['symbol']
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
            cursor.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
            conn.commit()
            self.notifier.send_text_message(chat_id, f"🗑️ 已移除对 {symbol} 的监控。", receive_id_type="chat_id")
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
            cursor.execute('SELECT symbol, name, entry_price, stop_loss FROM positions')
            positions = [f"**{row[1] or '未知'}** ({row[0]}) | 成本:{row[2]} | 止损:{row[3]}" for row in cursor.fetchall()]
            
            md = "**👀 观察池 (Watchlist)**\n"
            md += (", ".join(watchlist) if watchlist else "*暂无股票*") + "\n\n"
            md += "--- \n"
            md += "**🛡️ 持仓池 (Holdings)**\n"
            md += ("\n".join([f"- {p}" for p in positions]) if positions else "*暂无持仓*")
            
            self.notifier.send_interactive_message(chat_id, "📋 Frank 的监控清单", md, receive_id_type="chat_id")
        finally:
            conn.close()

    def process_instant_analysis(self, chat_id, symbol, name=""):
        """执行即时分析逻辑"""
        self.notifier.send_text_message(chat_id, f"🔍 收到指令！正在为 {name or symbol} 搜集资讯并建模...", receive_id_type="chat_id")
        
        news_df = get_stock_news(symbol)
        hist_df = get_stock_hist(symbol)
        current_price = get_stock_current_price(symbol)
        
        if news_df is None or news_df.empty:
            self.notifier.send_text_message(chat_id, f"⚠️ 暂时没有搜寻到关于 {symbol} 的近期资讯。", receive_id_type="chat_id")
            return

        title = str(news_df.iloc[0].get('新闻标题', news_df.iloc[0].get('title', '')))
        content = str(news_df.iloc[0].get('新闻内容', news_df.iloc[0].get('content', '')))
        ai_analysis = self.analyst.analyze_news(title, content, symbol=symbol)
        
        if not ai_analysis:
            self.notifier.send_text_message(chat_id, "❌ AI 分析过程出错，请检查 API 状态。", receive_id_type="chat_id")
            return

        plan = self.advisor.generate_plan(symbol, current_price, hist_df, ai_analysis)
        
        if plan:
            action = plan['action']
            emoji = "🎯" if "买入" in action else ("🛡️" if "减仓" in action else "💤")
            msg_title = f"{emoji} | {name or symbol} 综合建议"
            
            md = (
                f"💰 **当前价**: {current_price} 元\n"
                f"📈 **技术趋势**: {plan['trend']}\n\n"
                f"💡 **AI 核心结论**:\n> {ai_analysis.get('summary', '无')}\n\n"
                f"✅ **建议操作**: **{action}**\n"
                f"📊 **参考位**: 买入 {plan['buy_price'] or '--'} | 止损 {plan['stop_loss'] or '--'} | 止盈 {plan['take_profit'] or '--'}\n\n"
                f"📝 **逻辑分析**:\n{plan['reason']}"
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
