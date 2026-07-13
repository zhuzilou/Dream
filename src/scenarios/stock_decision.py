from dataclasses import dataclass
from typing import Any, Dict, List

from generator.card_renderer import CardSection, StructuredCard


@dataclass
class StockDecisionResult:
    card: StructuredCard
    data: Dict[str, Any]


class StockDecisionService:
    def build_decision(self, raw_question, stock, price_data, hist_df, news_summary=""):
        rows = self._rows(hist_df)
        metrics = self._metrics(rows)
        missing = []
        for key in ["price"]:
            if not price_data or price_data.get(key) in [None, 0, ""]:
                missing.append("当前价")
        if not rows:
            missing.append("历史K线")

        name = stock.get("name", "未知")
        symbol = stock.get("symbol", "未知")
        exchange = stock.get("exchange", self._infer_exchange(symbol))
        fallback = "存在数据降级" if price_data.get("is_fallback") else "未发现数据降级"

        evidence = [
            f"股票：{name} ({symbol})，交易所：{exchange}",
            f"当前价或最近收盘价：{price_data.get('price', '缺失')}，数据来源：{price_data.get('source', 'unknown')}",
            f"20日高低点：{metrics.get('high_20')} / {metrics.get('low_20')}",
            f"60日高低点：{metrics.get('high_60')} / {metrics.get('low_60')}",
            f"5日均线：{metrics.get('ma5')}，10日均线：{metrics.get('ma10')}，20日均线：{metrics.get('ma20')}",
            f"最近3-5个交易日成交量：{metrics.get('recent_volume')}",
            f"支撑位：{metrics.get('support')}，压力位：{metrics.get('resistance')}",
            f"数据状态：{fallback}" + (f"，缺失：{', '.join(missing)}" if missing else "")
        ]
        if news_summary:
            evidence.append(f"新闻辅助信息：{news_summary}")

        trigger_conditions = [
            "关键低点没有被有效跌破，并且收盘能守住支撑位。",
            "股价至少连续2个交易日站稳关键均线，避免一日游。",
            "成交量从放量下跌转为缩量企稳，说明卖压暂时减轻。",
            "反弹时出现放量修复，且次日没有快速跌回关键位下方。"
        ]
        invalidation_conditions = [
            "收盘有效跌破支撑位，或连续两天收在关键低点下方。",
            "放量修复失败后重新跌回原区间。",
            "数据恢复后与当前降级数据明显不一致。"
        ]
        checklist = [
            "有效跌破不是盘中碰一下，而是收盘跌破，或连续两天收在关键低点下方。",
            "站不稳是指只短暂摸到关键均线或关键位，随后收盘又跌回去。",
            "一日游是指只修复一天，第二天马上跌回原区间，说明修复不可靠。",
            "放量下跌表示卖压较强；缩量企稳要求成交量下降且股价不再创新低。",
            "放量修复不是盘中冲高，而是收盘站回关键位且成交量比前几天明显增加。",
            "轻仓试错是只用小比例仓位验证判断，错了能按失效条件退出。",
            "支撑位是下跌时需要重点观察能否守住的位置；压力位是反弹时需要观察能否突破的位置。"
        ]

        conclusion = "暂不因为下跌本身确认买入，更适合观察；条件满足时可以考虑轻仓试错。"
        card = StructuredCard(
            title=f"{name} ({symbol}) 个股买入决策与观察计划",
            conclusion=conclusion,
            metadata={"data_timestamp": price_data.get("timestamp", "当前分析时点")},
            sections=[
                CardSection("问题订正", [f"你问的是：{raw_question}", f"更适合分析为：{name} 当前是否出现低风险买点，若没有应等待哪些触发和失效条件。"]),
                CardSection("分析依据", evidence),
                CardSection("触发条件", trigger_conditions),
                CardSection("失效条件", invalidation_conditions),
                CardSection("仓位纪律", ["未满足条件前以观察为主；如条件满足，也只适合轻仓试错，由用户自行决定。"]),
                CardSection("观察 checklist", checklist),
                CardSection("下一步动作", ["不要只盯涨跌，下一次复核支撑位、关键均线、成交量和修复是否持续。"])
            ]
        )
        return StockDecisionResult(card=card, data=metrics)

    def _rows(self, hist_df):
        if hist_df is None:
            return []
        if hasattr(hist_df, "to_dict"):
            return hist_df.to_dict("records")
        return list(hist_df)

    def _metrics(self, rows):
        if not rows:
            return {}
        closes = [float(row["close"]) for row in rows if row.get("close") is not None]
        highs = [float(row["high"]) for row in rows if row.get("high") is not None]
        lows = [float(row["low"]) for row in rows if row.get("low") is not None]
        volumes = [float(row.get("volume", row.get("vol", 0)) or 0) for row in rows]
        return {
            "high_20": round(max(highs[-20:]), 2) if len(highs) >= 20 else "缺失",
            "low_20": round(min(lows[-20:]), 2) if len(lows) >= 20 else "缺失",
            "high_60": round(max(highs[-60:]), 2) if len(highs) >= 60 else "缺失",
            "low_60": round(min(lows[-60:]), 2) if len(lows) >= 60 else "缺失",
            "ma5": self._ma(closes, 5),
            "ma10": self._ma(closes, 10),
            "ma20": self._ma(closes, 20),
            "recent_volume": ", ".join([str(int(v)) for v in volumes[-5:]]) if volumes else "缺失",
            "support": round(min(lows[-20:]), 2) if len(lows) >= 20 else "缺失",
            "resistance": round(max(highs[-20:]), 2) if len(highs) >= 20 else "缺失"
        }

    def _ma(self, closes, days):
        if len(closes) < days:
            return "缺失"
        return round(sum(closes[-days:]) / days, 2)

    def _infer_exchange(self, symbol):
        if str(symbol).startswith("6"):
            return "SH"
        if str(symbol).startswith(("0", "3")):
            return "SZ"
        return "未知"
