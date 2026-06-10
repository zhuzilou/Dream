from loguru import logger
from strategist.technical_analysis import calculate_ma, get_support_resistance, analyze_trend

class TradeAdvisor:
    def __init__(self):
        pass

    def generate_plan(self, symbol, price_res, hist_df, ai_analysis, current_pos=None):
        """
        根据多维分析生成交易计划
        price_res: {"price": float, "is_fallback": bool}
        ai_analysis: {'sentiment_score': 6.5, 'summary': '...', 'devils_advocate': '...'}
        current_pos: {"quantity": float, "entry_price": float} or None
        """
        if hist_df is None or hist_df.empty:
            return None
            
        # 兼容性处理: 如果 price_res 是 float，则转换为 dict 格式
        if isinstance(price_res, (int, float)):
            price_res = {"price": float(price_res), "is_fallback": False}
        elif not isinstance(price_res, dict):
            price_res = {"price": 0.0, "is_fallback": False}

        current_price = price_res.get("price", 0)
        is_fallback = price_res.get("is_fallback", False)
        
        # 1. 计算技术指标
        hist_df = calculate_ma(hist_df)
        support, resistance = get_support_resistance(hist_df)
        trend = analyze_trend(hist_df)
        
        score = ai_analysis.get('sentiment_score', 0)
        summary = ai_analysis.get('summary', '无摘要')
        risk_point = ai_analysis.get('devils_advocate', '暂无明确风险提示')
        
        # 2. 状态识别
        has_pos = current_pos is not None and current_pos.get('quantity', 0) > 0
        pos_qty = current_pos.get('quantity', 0) if has_pos else 0
        
        plan = {
            "symbol": symbol,
            "current_price": current_price,
            "is_fallback": is_fallback,
            "trend": trend,
            "support": support,
            "resistance": resistance,
            "action": "保持观望",
            "buy_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": ""
        }
        
        # 3. 多维决策逻辑
        
        # A. 技术面结论
        tech_conclusion = f"当前处于 {trend}。支撑位 {support}，压力位 {resistance}。"
        
        # B. 决策引擎
        reasons = []
        scenarios = []
        if is_fallback:
            reasons.append("⚠️ 注意：当前基于延时数据分析。")
            
        if score >= 6: # 极佳
            if trend != "空头排列 (弱趋势)":
                if not has_pos:
                    plan["action"] = "建议建仓"
                    plan["buy_price"] = round(max(current_price * 0.99, support), 2)
                    reasons.append(f"AI 评分极高({score})，技术面未走坏。建议在支撑位附近建立底仓。")
                    scenarios.append(f"1. **如果** 明日企稳并放量突破 {resistance}，可追加 1 成仓。")
                    scenarios.append(f"2. **如果** 缩量回踩 {support} 不破，是最佳补仓点。")
                else:
                    plan["action"] = "建议加仓"
                    reasons.append(f"AI 持续利好({score})。现有持仓 {pos_qty}，可考虑回撤支撑位时加仓。")
                    scenarios.append(f"1. **如果** 股价站稳 {current_price}，建议持股待涨。")
            else:
                plan["action"] = "等待筑底"
                reasons.append(f"AI 虽利好，但技术面处于下降通道，建议观察支撑位 {support} 是否稳固。")
                scenarios.append(f"1. **如果** 在 {support} 附近出现长下影线或放量反弹，则确认底部。")
                
        elif score >= 3: # 偏好
            if has_pos:
                plan["action"] = "继续持仓"
                reasons.append("情绪偏暖，建议持有观望。")
                scenarios.append(f"1. **如果** 跌破 {support}，建议先行减仓规避风险。")
            else:
                plan["action"] = "分批轻仓"
                reasons.append("情绪中性偏好，可小量试探。")
                
        elif score <= -6: # 极差
            if has_pos:
                plan["action"] = "建议减仓/清仓"
                reasons.append(f"🚨 AI 提示重大利空({score})。技术面风险大，建议保护利润或止损。")
                scenarios.append(f"1. **如果** 明日不能快速收复 {current_price}，建议果断减仓 50%。")
                scenarios.append(f"2. **如果** 连续放量杀跌，则考虑空仓避险。")
            else:
                plan["action"] = "回避风险"
                reasons.append(f"AI 评分极低({score})，严禁入场。")
                scenarios.append(f"1. **如果** 市场整体情绪未回暖，哪怕出现小反弹也不要进场抢反弹。")
        else:
            plan["action"] = "继续观望"
            reasons.append(f"情绪中性({score})。暂无显著操作信号。")
            scenarios.append(f"1. **如果** 股价在 {support} 与 {resistance} 之间震荡，建议观望。")

        # 止损止盈建议 (通用)
        plan["stop_loss"] = round(support * 0.98, 2) if support else round(current_price * 0.95, 2)
        plan["take_profit"] = round(resistance * 1.05, 2) if resistance else round(current_price * 1.15, 2)
        
        # 组装结构化理由与推演
        plan["reason"] = ' '.join(reasons)
        plan["scenario_text"] = "\n".join(scenarios) if scenarios else "暂无明确推演，建议严格执行止损点。"
            
        return plan
