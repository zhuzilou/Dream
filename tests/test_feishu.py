import unittest
import os
import sys
import json
from unittest.mock import MagicMock, patch

# 将 src 目录添加到路径
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from notifier.feishu import FeishuBot

class TestFeishuBot(unittest.TestCase):
    def setUp(self):
        self.bot = FeishuBot()
        self.bot.token = "mock_token"

    @patch("requests.post")
    def test_send_interactive_message(self, mock_post):
        """验证卡片消息发送"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 0, "msg": "ok"}
        mock_post.return_value = mock_response
        
        self.bot.send_interactive_message("user_123", "测试标题", "**正文**")
        
        args, kwargs = mock_post.call_args
        payload = json.loads(kwargs['data'])
        self.assertEqual(payload['msg_type'], "interactive")
        content = json.loads(payload['content'])
        self.assertEqual(content['header']['title']['content'], "测试标题")
        self.assertEqual(content['elements'][0]['content'], "**正文**")

if __name__ == "__main__":
    unittest.main()
