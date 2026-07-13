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
            "reason": "",
            "confidence": "低",
            "trigger_conditions": [],
            "invalidation_conditions": [],
            "position_advice": "暂不加仓，等待更清晰的信号。",
            "review_plan": []
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
                    plan["action"] = "可轻仓试错"
                    plan["buy_price"] = round(max(current_price * 0.99, support), 2)
                    plan["confidence"] = "中高" if not is_fallback else "中"
                    plan["position_advice"] = "首次只建观察仓，建议不超过计划仓位的 20%-30%。"
                    reasons.append(f"AI 评分较高({score})，技术面暂未走坏，可观察支撑位附近是否出现低风险试错条件。")
                    scenarios.append(f"1. **如果** 明日企稳并放量突破 {resistance}，条件满足时可以考虑小比例试错。")
                    scenarios.append(f"2. **如果** 缩量回踩 {support} 不破，可继续观察是否形成更稳的确认点。")
                    plan["trigger_conditions"].extend([
                        f"股价企稳并放量突破压力位 {resistance}",
                        f"回踩支撑位 {support} 附近不破且成交量未异常放大"
                    ])
                else:
                    plan["action"] = "可观察"
                    plan["confidence"] = "中高" if not is_fallback else "中"
                    plan["position_advice"] = "已有持仓只考虑分批加仓，单次不超过现有仓位的 20%。"
                    reasons.append(f"AI 持续偏暖({score})。现有持仓 {pos_qty}，可观察回撤支撑位时是否仍守住失效条件。")
                    scenarios.append(f"1. **如果** 股价站稳 {current_price}，建议持股待涨。")
                    plan["trigger_conditions"].extend([
                        f"股价站稳当前价 {current_price}",
                        f"回撤不跌破支撑位 {support}"
                    ])
            else:
                plan["action"] = "等待确认"
                plan["confidence"] = "中"
                plan["position_advice"] = "不追高，不加仓，只等待筑底确认。"
                reasons.append(f"AI 虽利好，但技术面处于下降通道，建议观察支撑位 {support} 是否稳固。")
                scenarios.append(f"1. **如果** 在 {support} 附近出现长下影线或放量反弹，则确认底部。")
                plan["trigger_conditions"].append(f"支撑位 {support} 附近出现明确止跌信号")
                
        elif score >= 3: # 偏好
            if has_pos:
                plan["action"] = "继续持仓"
                plan["confidence"] = "中"
                plan["position_advice"] = "维持现有仓位，不因单条偏暖消息主动加仓。"
                reasons.append("情绪偏暖，建议持有观望。")
                scenarios.append(f"1. **如果** 跌破 {support}，建议先行减仓规避风险。")
                plan["trigger_conditions"].append(f"股价继续维持在支撑位 {support} 上方")
            else:
                plan["action"] = "可轻仓试错"
                plan["confidence"] = "中"
                plan["position_advice"] = "仅适合轻仓试探，建议不超过计划仓位的 10%-20%。"
                reasons.append("情绪中性偏好，但仍需用小仓位验证，条件不满足时继续观察。")
                plan["trigger_conditions"].append(f"股价不跌破支撑位 {support} 且板块情绪未走弱")
                
        elif score <= -6: # 极差
            if has_pos:
                plan["action"] = "降低仓位风险"
                plan["confidence"] = "高" if not is_fallback else "中高"
                plan["position_advice"] = "优先控制风险，可按失效条件降低仓位暴露，最终操作由用户决定。"
                reasons.append(f"🚨 AI 提示重大利空({score})。技术面风险大，建议保护利润或止损。")
                scenarios.append(f"1. **如果** 明日不能快速收复 {current_price}，可考虑先降低仓位风险。")
                scenarios.append(f"2. **如果** 连续放量杀跌，应以回避风险为主。")
                plan["trigger_conditions"].append("出现反弹但无法收复关键价位时优先减仓")
            else:
                plan["action"] = "回避风险"
                plan["confidence"] = "高" if not is_fallback else "中高"
                plan["position_advice"] = "不新开仓，等待利空消化和技术面修复。"
                reasons.append(f"AI 评分偏低({score})，暂不满足买入条件。")
                scenarios.append(f"1. **如果** 市场整体情绪未回暖，哪怕出现小反弹也不要进场抢反弹。")
                plan["trigger_conditions"].append("暂不设置买入触发，先等待风险释放")
        else:
            plan["action"] = "继续观望"
            plan["confidence"] = "低"
            plan["position_advice"] = "保持现金或原仓位，不为了交易而交易。"
            reasons.append(f"情绪中性({score})。暂无显著操作信号。")
            scenarios.append(f"1. **如果** 股价在 {support} 与 {resistance} 之间震荡，建议观望。")
            plan["trigger_conditions"].append(f"等待股价有效突破 {resistance} 或回踩 {support} 后企稳")

        # 止损止盈建议 (通用)
        plan["stop_loss"] = round(support * 0.98, 2) if support else round(current_price * 0.95, 2)
        plan["take_profit"] = round(resistance * 1.05, 2) if resistance else round(current_price * 1.15, 2)
        plan["invalidation_conditions"].extend([
            f"有效跌破支撑位 {support}",
            f"跌破止损位 {plan['stop_loss']}",
            "新闻逻辑被后续公告或市场表现证伪"
        ])
        if is_fallback:
            plan["invalidation_conditions"].append("实时行情恢复后与当前价格偏差较大")
        plan["review_plan"].extend([
            "1 个交易日后检查是否触发买入/减仓条件",
            "3 个交易日后复核支撑位、压力位和成交量变化",
            "5 个交易日后记录建议结果，用于校准 Frank 的判断"
        ])
        
        # 组装结构化理由与推演
        plan["reason"] = ' '.join(reasons)
        plan["scenario_text"] = "\n".join(scenarios) if scenarios else "暂无明确推演，建议严格执行止损点。"
            
        return plan
