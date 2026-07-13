import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# AGENT_WORKFLOW_TEST
# workflow_instance: dream/frank-gemini-agent-v1.2
# feature: Frank Gemini Agent V1.2

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if "akshare" not in sys.modules:
    sys.modules["akshare"] = MagicMock()
if "loguru" not in sys.modules:
    mock_loguru = MagicMock()
    mock_loguru.logger = MagicMock()
    sys.modules["loguru"] = mock_loguru

from generator.card_renderer import CardSection, StructuredCard, render_markdown
from listener.intent_router import IntentType, route_intent
from memory.observation_memory import ObservationMemory
from memory.term_learning import TermLearningQueue
from scraper.akshare_client import collect_board_observation_inputs
from scenarios.board_observation import BoardObservationService
from scenarios.stock_decision import StockDecisionService


class TestV12AgentWorkflow(unittest.TestCase):
    def make_hist_df(self):
        rows = []
        for i in range(1, 66):
            rows.append({
                "date": f"2026-06-{(i % 28) + 1:02d}",
                "open": 9.5 + i * 0.01,
                "close": 10 + i * 0.03,
                "high": 10.5 + i * 0.03,
                "low": 9.2 + i * 0.02,
                "volume": 100000 + i * 2000
            })
        return rows

    def test_intent_router_maps_v12_entrypoints(self):
        self.assertEqual(route_intent("上海电力最近一直在跌，可以买入吗？").intent_type, IntentType.SCENARIO_STOCK_DECISION)
        self.assertEqual(route_intent("不知道买什么，帮我推荐几支股票").intent_type, IntentType.SCENARIO_BOARD_OBSERVATION)
        self.assertEqual(route_intent("记录术语 放量修复 场景7.1").intent_type, IntentType.TERM_LEARNING)
        self.assertEqual(route_intent("复盘观察池 1").intent_type, IntentType.OBSERVATION_REVIEW)
        self.assertEqual(route_intent("审核").intent_type, IntentType.DEPRECATED_AUDIT)

    def test_structured_card_renders_required_sections(self):
        card = StructuredCard(
            title="测试卡片",
            conclusion="这是结论",
            sections=[
                CardSection("分析依据", ["数据1", "数据2"]),
                CardSection("触发条件", ["条件1"]),
                CardSection("风险", ["风险1"]),
                CardSection("下一步", ["动作1"])
            ],
            metadata={"data_timestamp": "2026-07-12 15:00:00"}
        )

        md = render_markdown(card)

        self.assertIn("这是结论", md)
        self.assertIn("分析依据", md)
        self.assertIn("触发条件", md)
        self.assertIn("风险", md)
        self.assertIn("下一步", md)
        self.assertIn("2026-07-12 15:00:00", md)

    def test_stock_decision_outputs_data_conditions_and_term_explanations(self):
        service = StockDecisionService()
        result = service.build_decision(
            raw_question="上海电力最近一直在跌，可以买入吗？",
            stock={"symbol": "600021", "name": "上海电力", "exchange": "SH"},
            price_data={"price": 10.52, "source": "mock", "is_fallback": False},
            hist_df=self.make_hist_df(),
            news_summary="暂无重大新闻，主要看价格和成交量。"
        )

        md = render_markdown(result.card)

        self.assertIn("问题订正", md)
        self.assertIn("结论先行", md)
        self.assertIn("20日", md)
        self.assertIn("60日", md)
        self.assertIn("5日均线", md)
        self.assertIn("成交量", md)
        self.assertIn("触发条件", md)
        self.assertIn("失效条件", md)
        self.assertIn("观察 checklist", md)
        self.assertIn("有效跌破不是盘中碰一下", md)
        self.assertNotIn("建议建仓", md)
        self.assertNotIn("建议加仓", md)
        self.assertNotIn("最佳补仓点", md)
        self.assertNotIn("严禁入场", md)
        self.assertNotIn("果断减仓", md)

    def test_board_observation_persists_pool_and_marks_intraday(self):
        db_fd, db_path = tempfile.mkstemp()
        os.close(db_fd)
        try:
            memory = ObservationMemory(db_path)
            memory.init_schema()
            service = BoardObservationService(memory=memory)

            result = service.build_observation(
                market_summary="指数震荡，资金更偏向低位修复。",
                boards=[{
                    "board_name": "电力",
                    "change_pct": 2.1,
                    "net_inflow": 120000000,
                    "turnover": 3000000000,
                    "sustainability": 0.8,
                    "beginner_friendliness": 0.7,
                    "stocks": [
                        {"symbol": "600021", "name": "上海电力", "turnover": 900000000, "change_pct": 3.2, "is_st": False, "is_suspended": False},
                        {"symbol": "600023", "name": "浙能电力", "turnover": 700000000, "change_pct": 2.4, "is_st": False, "is_suspended": False},
                        {"symbol": "600999", "name": "过热样本", "turnover": 100000000, "change_pct": 10.0, "is_st": False, "is_suspended": False}
                    ]
                }],
                data_timestamp=datetime(2026, 7, 12, 14, 30),
                is_intraday=True
            )

            md = render_markdown(result.card)
            run = memory.get_run(result.run_id)
            stocks = memory.list_stocks(result.run_id)

            self.assertIn("观察池，不是买入名单", md)
            self.assertIn("盘中临时观察版", md)
            self.assertIn("置信度降低", md)
            self.assertEqual(run["status"], "intraday")
            self.assertLessEqual(len(stocks), 2)
            self.assertTrue(all(stock["symbol"] != "600999" for stock in stocks))
        finally:
            os.remove(db_path)

    def test_term_learning_queue_records_lists_and_exports_explicit_terms(self):
        db_fd, db_path = tempfile.mkstemp()
        os.close(db_fd)
        try:
            queue = TermLearningQueue(db_path)
            queue.init_schema()
            term_id = queue.record_term("放量修复", "记录术语 放量修复 场景7.1", related_scene="场景7.1")

            pending = queue.list_pending()
            recent = queue.list_recent(limit=5)
            exported = queue.export_records()

            self.assertEqual(term_id, 1)
            self.assertEqual(pending[0]["term"], "放量修复")
            self.assertEqual(recent[0]["status"], "new")
            self.assertIn("放量修复", exported)
            self.assertIn("场景7.1", exported)
        finally:
            os.remove(db_path)

    @patch("scraper.akshare_client.ak")
    def test_collect_board_observation_inputs_uses_akshare_board_data(self, mock_ak):
        pd = __import__("pandas")
        mock_ak.stock_board_industry_name_em.return_value = pd.DataFrame([
            {"板块名称": "电力", "涨跌幅": 2.1, "主力净流入": 120000000, "成交额": 3000000000},
            {"板块名称": "机器人", "涨跌幅": 1.2, "主力净流入": 80000000, "成交额": 2000000000}
        ])
        mock_ak.stock_board_industry_cons_em.return_value = pd.DataFrame([
            {"代码": "600021", "名称": "上海电力", "成交额": 900000000, "涨跌幅": 3.2},
            {"代码": "600023", "名称": "浙能电力", "成交额": 700000000, "涨跌幅": 2.4}
        ])

        boards = collect_board_observation_inputs(max_boards=1)

        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0]["board_name"], "电力")
        self.assertEqual(boards[0]["net_inflow"], 120000000)
        self.assertEqual(boards[0]["stocks"][0]["symbol"], "600021")
        self.assertFalse(boards[0]["stocks"][0]["is_st"])


if __name__ == "__main__":
    unittest.main()
