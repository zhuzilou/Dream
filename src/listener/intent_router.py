import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IntentType(Enum):
    SCENARIO_STOCK_DECISION = "scenario_stock_decision"
    SCENARIO_BOARD_OBSERVATION = "scenario_board_observation"
    TERM_LEARNING = "term_learning"
    OBSERVATION_REVIEW = "observation_review"
    LEGACY_WATCHLIST = "legacy_watchlist"
    LEGACY_POSITION = "legacy_position"
    DEPRECATED_AUDIT = "deprecated_audit"
    HELP = "help"
    CHAT_FALLBACK = "chat_fallback"


@dataclass
class IntentResult:
    intent_type: IntentType
    raw_text: str
    argument: str = ""
    stock_query: Optional[str] = None


def route_intent(text: str) -> IntentResult:
    raw_text = (text or "").strip()
    compact = re.sub(r"\s+", "", raw_text)

    if compact in ["帮助", "help", "菜单", "指令"]:
        return IntentResult(IntentType.HELP, raw_text)

    if compact.startswith("记录术语") or compact in ["待补充术语", "术语记录", "导出术语记录"]:
        return IntentResult(IntentType.TERM_LEARNING, raw_text, argument=raw_text)

    if compact.startswith("复盘观察池") or compact in ["查看观察池", "最近观察池"]:
        return IntentResult(IntentType.OBSERVATION_REVIEW, raw_text, argument=raw_text)

    if "审核" in compact:
        return IntentResult(IntentType.DEPRECATED_AUDIT, raw_text)

    if compact.startswith("监控") or "加入观察池" in compact:
        return IntentResult(IntentType.LEGACY_WATCHLIST, raw_text, argument=raw_text)

    if compact.startswith("买入") or compact.startswith("卖出") or compact.startswith("移除") or compact.startswith("删"):
        return IntentResult(IntentType.LEGACY_POSITION, raw_text, argument=raw_text)

    if compact in ["持仓分析", "分析持仓", "体检", "诊断"]:
        return IntentResult(IntentType.CHAT_FALLBACK, raw_text)

    board_keywords = ["最近有哪些板块值得关注", "有什么股票值得关注", "不知道接下来该看什么", "收盘后帮我看方向",
                      "选股", "推荐", "买什么", "最近看什么"]
    if any(keyword in compact for keyword in board_keywords):
        return IntentResult(IntentType.SCENARIO_BOARD_OBSERVATION, raw_text)

    stock_keywords = [
        "股票能买吗", "能买吗", "能不能买", "可以买入吗", "可以买入", "可以买吗", "可以买吗",
        "能买了吗", "可以抄底吗", "最近一直跌", "一直跌", "买点", "走势"
    ]
    is_analysis_request = (
        compact.startswith("分析") or compact.startswith("评价") or compact.startswith("看看")
    ) and compact not in ["分析持仓"]
    if re.search(r"\d{6}", compact) or is_analysis_request or any(keyword in compact for keyword in stock_keywords):
        return IntentResult(IntentType.SCENARIO_STOCK_DECISION, raw_text, stock_query=raw_text)

    return IntentResult(IntentType.CHAT_FALLBACK, raw_text)
