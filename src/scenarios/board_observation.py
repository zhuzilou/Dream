from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from generator.card_renderer import CardSection, StructuredCard


@dataclass
class BoardObservationResult:
    card: StructuredCard
    run_id: int
    boards: List[Dict[str, Any]]


class BoardObservationService:
    def __init__(self, memory):
        self.memory = memory

    def build_observation(self, market_summary, boards, data_timestamp, is_intraday=False):
        status = "intraday" if is_intraday else "after_close"
        timestamp_text = data_timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(data_timestamp, "strftime") else str(data_timestamp)
        trade_date = timestamp_text[:10]
        run_id = self.memory.create_run(trade_date, market_summary, timestamp_text, status)

        board_sections = []
        saved_boards = []
        for board in sorted(boards, key=self._score_board, reverse=True):
            level = self._level(board)
            reason = self._board_reason(board)
            risk_note = "盘中数据仍在变化，收盘后需要重新生成正式观察池。" if is_intraday else "仍需逐只进入场景一确认。"
            board_id = self.memory.add_board(run_id, board.get("board_name", "未知板块"), level, reason, risk_note)
            candidates = self._candidates(board)
            saved_candidates = []
            for stock in candidates:
                observe_conditions = [
                    "次日不能高开低走。",
                    "观察能否站稳关键均线。",
                    "反弹需要放量修复，且不能一日游。"
                ]
                invalidation_conditions = [
                    "有效跌破关键低点。",
                    "放量修复失败后跌回原区间。"
                ]
                self.memory.add_stock(
                    run_id, board_id, stock.get("symbol"), stock.get("name"),
                    f"所在板块 {board.get('board_name')} 有资金和活跃度支持。",
                    observe_conditions, invalidation_conditions
                )
                saved_candidates.append(f"{stock.get('name')}({stock.get('symbol')})：观察能否站稳关键均线，避免一日游。")
            saved_boards.append({"board_name": board.get("board_name"), "level": level, "stocks": saved_candidates})
            board_sections.append(CardSection(f"{level} 类：{board.get('board_name')}", [reason, risk_note] + saved_candidates))

        version = "盘中临时观察版" if is_intraday else "收盘后正式观察池"
        confidence_note = "盘中数据仍在变化，置信度降低，不作为买入依据。" if is_intraday else "基于收盘后相对稳定数据。"
        card = StructuredCard(
            title="板块观察池与教学复盘",
            conclusion=f"我不会直接给买入名单，我会先生成观察池。本次为{version}，{confidence_note}",
            metadata={"data_timestamp": timestamp_text},
            sections=[
                CardSection("任务边界", ["这是观察池，不是买入名单；具体买卖需要逐只进入场景一继续判断。"]),
                CardSection("今日市场环境", [market_summary]),
            ] + board_sections + [
                CardSection("下一步动作", ["未来1-3个交易日复盘观察条件是否成立，而不是用涨跌证明 Frank 推荐正确。"])
            ]
        )
        return BoardObservationResult(card=card, run_id=run_id, boards=saved_boards)

    def _score_board(self, board):
        net_inflow = float(board.get("net_inflow", 0) or 0)
        change_pct = float(board.get("change_pct", 0) or 0)
        turnover = float(board.get("turnover", 0) or 0)
        sustainability = float(board.get("sustainability", 0) or 0)
        beginner = float(board.get("beginner_friendliness", 0) or 0)
        return (
            min(net_inflow / 100000000, 10) * 0.30 +
            min(max(change_pct, 0), 10) * 0.20 +
            min(turnover / 1000000000, 10) * 0.20 +
            sustainability * 10 * 0.20 +
            beginner * 10 * 0.10
        )

    def _level(self, board):
        score = self._score_board(board)
        if score >= 6:
            return "A"
        if score >= 4:
            return "B"
        if score >= 2:
            return "C"
        return "D"

    def _board_reason(self, board):
        return (
            f"资金流 {board.get('net_inflow', 0)}，涨跌幅 {board.get('change_pct', 0)}%，"
            f"成交额/活跃度 {board.get('turnover', 0)}，不是只按涨幅排序。"
        )

    def _candidates(self, board):
        stocks = []
        for stock in board.get("stocks", []):
            if stock.get("is_st") or stock.get("is_suspended"):
                continue
            if float(stock.get("change_pct", 0) or 0) >= 9.8:
                continue
            if float(stock.get("turnover", 0) or 0) <= 0:
                continue
            stocks.append(stock)
        stocks.sort(key=lambda item: float(item.get("turnover", 0) or 0), reverse=True)
        return stocks[:2]
