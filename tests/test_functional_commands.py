import os
import sys
import unittest
import sqlite3
import json
import tempfile
import shutil
import types
import importlib.util
from unittest.mock import MagicMock, patch

# Ensure src is in path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Mock modules that might be missing in some environments
sys.modules['schedule'] = MagicMock()
if 'akshare' not in sys.modules:
    sys.modules['akshare'] = MagicMock()
if 'pandas' not in sys.modules and importlib.util.find_spec('pandas') is None:
    mock_pandas = MagicMock()
    mock_pandas.DataFrame = MagicMock
    sys.modules['pandas'] = mock_pandas
if 'numpy' not in sys.modules and importlib.util.find_spec('numpy') is None:
    sys.modules['numpy'] = MagicMock()
if 'requests' not in sys.modules and importlib.util.find_spec('requests') is None:
    sys.modules['requests'] = MagicMock()
if 'loguru' not in sys.modules and importlib.util.find_spec('loguru') is None:
    mock_loguru = MagicMock()
    mock_loguru.logger = MagicMock()
    sys.modules['loguru'] = mock_loguru
if 'dotenv' not in sys.modules:
    mock_dotenv = MagicMock()
    mock_dotenv.load_dotenv = MagicMock()
    sys.modules['dotenv'] = mock_dotenv
if 'lark_oapi' not in sys.modules:
    mock_lark = types.ModuleType("lark_oapi")
    mock_lark.LogLevel = MagicMock(INFO="INFO")
    mock_lark.EventDispatcherHandler = MagicMock()
    sys.modules['lark_oapi'] = mock_lark
    sys.modules['lark_oapi.api'] = types.ModuleType("lark_oapi.api")
    sys.modules['lark_oapi.api.im'] = types.ModuleType("lark_oapi.api.im")
    mock_im_v1 = types.ModuleType("lark_oapi.api.im.v1")
    mock_im_v1.P2ImMessageReceiveV1 = MagicMock
    sys.modules['lark_oapi.api.im.v1'] = mock_im_v1
    mock_ws = types.ModuleType("lark_oapi.ws")
    mock_ws.Client = MagicMock()
    sys.modules['lark_oapi.ws'] = mock_ws

import main
import listener.feishu_listener as feishu_listener
from memory.observation_memory import ObservationMemory

class TestFunctionalCommands(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_scout.db")
        
        # Patch DB_PATH in modules
        main.DB_PATH = self.db_path
        feishu_listener.DB_PATH = self.db_path
        
        os.environ["FEISHU_APP_ID"] = "test_id"
        os.environ["FEISHU_APP_SECRET"] = "test_secret"
        
        self.listener = feishu_listener.FeishuListener()
        self.listener.notifier.send_text_message = MagicMock()
        self.listener.notifier.send_interactive_message = MagicMock()
        
        main.init_db()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_db_migration_logic(self):
        """验证数据库迁移逻辑"""
        # 1. 创建旧表
        conn = sqlite3.connect(self.db_path)
        conn.execute("DROP TABLE IF EXISTS watchlist")
        conn.execute("CREATE TABLE watchlist (symbol TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()
        
        # 2. 运行 init_db 触发迁移
        main.init_db()
        
        # 3. 检查列
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(watchlist)")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn('name', columns)
        conn.close()

    @patch("listener.feishu_listener.resolve_stock_symbol")
    def test_command_monitoring(self, mock_resolve):
        """验证‘监控’指令"""
        mock_resolve.return_value = {'symbol': '301667', 'name': '纳百川'}
        
        mock_event = MagicMock()
        mock_event.event.message.chat_id = "chat_123"
        mock_event.event.message.content = json.dumps({"text": "监控 纳百川"})
        mock_event.event.message.parent_id = None
        mock_event.event.message.root_id = None
        
        self.listener.handle_message(mock_event)
        
        # 验证卡片内容
        self.assertTrue(self.listener.notifier.send_interactive_message.called)
        args = self.listener.notifier.send_interactive_message.call_args[0]
        self.assertIn("纳百川 (301667)", args[2])

    def test_command_pool_listing(self):
        """验证‘池子’指令"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO watchlist (symbol, name) VALUES ("000001", "平安银行")')
        conn.commit()
        conn.close()
        
        mock_event = MagicMock()
        mock_event.event.message.content = json.dumps({"text": "池子"})
        mock_event.event.message.parent_id = None
        mock_event.event.message.root_id = None
        
        self.listener.handle_message(mock_event)
        
        last_call_text = self.listener.notifier.send_interactive_message.call_args[0][2]
        self.assertIn("平安银行(000001)", last_call_text)

    @patch("listener.feishu_listener.resolve_stock_symbol")
    def test_natural_language_analysis_extracts_stock_name(self, mock_resolve):
        """验证自然语言问题能提取股票名并进入场景一"""
        def fake_resolve(query):
            if query == "上海电力":
                return {'symbol': '600021', 'name': '上海电力'}
            return None

        mock_resolve.side_effect = fake_resolve
        self.listener.handle_stock_decision = MagicMock()

        mock_event = MagicMock()
        mock_event.event.message.message_id = "msg_natural_analysis"
        mock_event.event.message.chat_id = "chat_123"
        mock_event.event.message.content = json.dumps({"text": "分析下上海电力的走势情况，是否有合适的买入点"})
        mock_event.event.message.parent_id = None
        mock_event.event.message.root_id = None

        self.listener.handle_message(mock_event)

        self.listener.handle_stock_decision.assert_called_once_with(
            "chat_123",
            "600021",
            "上海电力",
            "分析下上海电力的走势情况，是否有合适的买入点"
        )

    @patch("listener.feishu_listener.resolve_stock_symbol")
    def test_common_stock_questions_enter_v12_decision_flow(self, mock_resolve):
        """验证常见个股问法不会落回旧即时分析流程"""
        def fake_resolve(query):
            if query == "上海电力":
                return {'symbol': '600021', 'name': '上海电力'}
            return None

        mock_resolve.side_effect = fake_resolve
        self.listener.handle_stock_decision = MagicMock()
        self.listener.process_instant_analysis = MagicMock()

        for index, text in enumerate(["上海电力最近一直跌，可以买吗", "分析 上海电力", "评价 上海电力"]):
            self.listener.handle_stock_decision.reset_mock()
            self.listener.process_instant_analysis.reset_mock()
            mock_event = MagicMock()
            mock_event.event.message.message_id = f"msg_stock_question_{index}"
            mock_event.event.message.chat_id = "chat_123"
            mock_event.event.message.content = json.dumps({"text": text})
            mock_event.event.message.parent_id = None
            mock_event.event.message.root_id = None

            self.listener.handle_message(mock_event)

            self.listener.handle_stock_decision.assert_called_once_with("chat_123", "600021", "上海电力", text)
            self.listener.process_instant_analysis.assert_not_called()

    def test_recommendation_request_enters_board_observation(self):
        """验证推荐类请求进入场景二而不是旧荐股逻辑"""
        self.listener.handle_board_observation = MagicMock()

        mock_event = MagicMock()
        mock_event.event.message.message_id = "msg_recommend"
        mock_event.event.message.chat_id = "chat_123"
        mock_event.event.message.content = json.dumps({"text": "不知道买什么，帮我推荐几支股票"})
        mock_event.event.message.parent_id = None
        mock_event.event.message.root_id = None

        self.listener.handle_message(mock_event)

        self.listener.handle_board_observation.assert_called_once_with("chat_123", "不知道买什么，帮我推荐几支股票")

    @patch("listener.feishu_listener.collect_board_observation_inputs")
    def test_board_observation_empty_data_does_not_create_fake_pool(self, mock_collect):
        """验证板块数据为空时不写入假的观察方向"""
        mock_collect.return_value = []

        self.listener.handle_board_observation("chat_123", "最近有哪些板块值得关注")

        md = self.listener.notifier.send_interactive_message.call_args[0][2]
        self.assertIn("板块数据暂不可用", md)
        self.assertIn("未生成观察池", md)
        self.assertNotIn("数据待确认方向", md)

        conn = sqlite3.connect(self.db_path)
        run_status = conn.execute("SELECT status FROM observation_runs ORDER BY id DESC LIMIT 1").fetchone()[0]
        board_count = conn.execute("SELECT COUNT(*) FROM observation_boards").fetchone()[0]
        stock_count = conn.execute("SELECT COUNT(*) FROM observation_stocks").fetchone()[0]
        conn.close()

        self.assertEqual(run_status, "failed")
        self.assertEqual(board_count, 0)
        self.assertEqual(stock_count, 0)

    @patch("listener.feishu_listener.get_stock_hist")
    def test_observation_review_writes_review_record(self, mock_hist):
        """验证复盘观察池会写入 observation_reviews，而不是只列出观察池"""
        mock_hist.return_value = [
            {"date": "2026-07-14", "close": 10.1, "high": 10.3, "low": 9.8, "volume": 100000},
            {"date": "2026-07-15", "close": 10.4, "high": 10.6, "low": 10.0, "volume": 130000}
        ]
        memory = ObservationMemory(self.db_path)
        memory.init_schema()
        run_id = memory.create_run("2026-07-13", "测试市场环境", "2026-07-13 15:30:00", "after_close")
        board_id = memory.add_board(run_id, "电力", "B", "资金活跃", "需逐只确认")
        memory.add_stock(
            run_id, board_id, "600021", "上海电力", "电力板块候选",
            ["观察能否站稳关键均线", "反弹需要放量修复"],
            ["有效跌破关键低点"]
        )

        self.listener.handle_observation_memory("chat_123", f"复盘观察池 {run_id}")

        md = self.listener.notifier.send_interactive_message.call_args[0][2]
        conn = sqlite3.connect(self.db_path)
        review_count = conn.execute("SELECT COUNT(*) FROM observation_reviews").fetchone()[0]
        conn.close()

        self.assertEqual(review_count, 1)
        self.assertIn("复盘用于学习", md)
        self.assertIn("条件是否成立", md)
        self.assertIn("上海电力(600021)", md)

    def test_help_uses_v12_product_language(self):
        """验证帮助文案不再宣传旧版定时资讯推送和加减仓建议"""
        self.listener.send_help("chat_123")

        md = self.listener.notifier.send_interactive_message.call_args[0][2]

        self.assertIn("个股能不能买", md)
        self.assertIn("板块观察池", md)
        self.assertIn("复盘观察池", md)
        self.assertIn("记录术语", md)
        self.assertNotIn("每日 3 次", md)
        self.assertNotIn("加减仓建议", md)
        self.assertNotIn("高频风险盯盘", md)

    def test_audit_command_is_deprecated_main_flow(self):
        """验证审核不再进入 RiskAuditor 主流程"""
        self.listener.handle_audit = MagicMock()

        mock_event = MagicMock()
        mock_event.event.message.message_id = "msg_audit"
        mock_event.event.message.chat_id = "chat_123"
        mock_event.event.message.content = json.dumps({"text": "审核"})
        mock_event.event.message.parent_id = None
        mock_event.event.message.root_id = None

        self.listener.handle_message(mock_event)

        self.listener.handle_audit.assert_not_called()
        args = self.listener.notifier.send_interactive_message.call_args[0]
        self.assertIn("已降级", args[2])
        self.assertIn("具体股票", args[2])

    def test_blank_parent_reply_does_not_trigger_risk_auditor(self):
        """验证空白回复父消息不会绕过 V1.2 降级边界进入 RiskAuditor"""
        self.listener.handle_audit = MagicMock()
        self.listener.notifier.get_message_content = MagicMock(return_value="父消息里的一段市场观点")

        mock_event = MagicMock()
        mock_event.event.message.message_id = "msg_blank_reply"
        mock_event.event.message.chat_id = "chat_123"
        mock_event.event.message.content = json.dumps({"text": ""})
        mock_event.event.message.parent_id = "parent_msg_1"
        mock_event.event.message.root_id = None

        self.listener.handle_message(mock_event)

        self.listener.notifier.get_message_content.assert_not_called()
        self.listener.handle_audit.assert_not_called()
        args = self.listener.notifier.send_interactive_message.call_args[0]
        self.assertIn("已降级", args[2])

    def test_init_db_creates_v12_memory_tables(self):
        """验证 V1.2 记忆表会随数据库初始化创建"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for table in [
            "observation_runs",
            "observation_boards",
            "observation_stocks",
            "observation_reviews",
            "term_learning_queue"
        ]:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            self.assertIsNotNone(cursor.fetchone(), table)

        conn.close()

    def test_legacy_news_push_scheduler_disabled_by_default(self):
        """验证定时新闻直接推送默认不再作为主功能注册"""
        if "FRANK_ENABLE_LEGACY_NEWS_PUSH" in os.environ:
            del os.environ["FRANK_ENABLE_LEGACY_NEWS_PUSH"]

        main.schedule.reset_mock()

        main.configure_scheduler()

        self.assertFalse(main.schedule.every.called)

if __name__ == "__main__":
    unittest.main()
