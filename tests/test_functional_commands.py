import os
import sys
import unittest
import sqlite3
import json
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Ensure src is in path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Mock modules that might be missing in some environments
sys.modules['schedule'] = MagicMock()
if 'akshare' not in sys.modules:
    sys.modules['akshare'] = MagicMock()

import main
import listener.feishu_listener as feishu_listener

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

if __name__ == "__main__":
    unittest.main()
