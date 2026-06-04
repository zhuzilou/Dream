from loguru import logger
from strategist.technical_analysis import calculate_ma, get_support_resistance, analyze_trend

class TradeAdvisor:
    def __init__(self):
        pass

    def generate_plan(self, symbol, current_price, hist_df, ai_analysis):
        """
        根据 AI 分析和技术面生成交易计划
        ai_analysis: {'sentiment_score': 6.5, 'summary': '...', 'devils_advocate': '...'}
        """
        if hist_df is None or hist_df.empty:
            return None
            
        # 1. 计算技术指标
        hist_df = calculate_ma(hist_df)
        support, resistance = get_support_resistance(hist_df)
        trend = analyze_trend(hist_df)
        
        score = ai_analysis.get('sentiment_score', 0)
        summary = ai_analysis.get('summary', '无摘要')
        
        plan = {
            "symbol": symbol,
            "current_price": current_price,
            "trend": trend,
            "support": support,
            "resistance": resistance,
            "action": "观望",
            "buy_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": ""
        }
        
        # 2. 决策逻辑 (示例)
        # 如果利好 (>5) 且 趋势不是极弱
        if score >= 6:
            if trend != "空头排列 (弱趋势)":
                plan["action"] = "建议买入/持仓"
                # 建议在支撑位附近买入，或者当前价买入
                plan["buy_price"] = round(max(current_price * 0.98, support), 2)
                plan["stop_loss"] = round(plan["buy_price"] * 0.95, 2)
                plan["take_profit"] = round(current_price * 1.10, 2)
                plan["reason"] = f"AI 利好评分 {score} ({summary})。技术面呈 {trend}，建议依托支撑位分批介入。"
            else:
                plan["reason"] = f"AI 虽有利好评分 {score} ({summary})，但技术面处于下降通道，建议等待筑底。"
        elif score <= -6:
            plan["action"] = "建议减仓/避险"
            plan["reason"] = f"AI 提示重大风险 {score} ({summary})。请注意仓位控制。"
        else:
            plan["reason"] = f"情绪中性 ({score}: {summary})。目前无显著操作信号，建议保持观望。"
            
        return plan
