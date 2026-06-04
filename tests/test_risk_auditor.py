import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# 将 src 加入路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from analyst.risk_auditor import RiskAuditor

class TestRiskAuditor(unittest.TestCase):
    def setUp(self):
        os.environ["MINIMAX_API_KEY"] = "test_key"
        self.auditor = RiskAuditor()

    @patch("requests.post")
    def test_audit_success(self, mock_post):
        # 模拟 API 返回
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "这是一个 **模拟的审计报告**。风险很高。"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        content = "买入贵州茅台，稳赚不赔。"
        market_context = "- 贵州茅台 (600519): 现价 1600 元"
        
        result = self.auditor.audit(content, market_context)
        
        self.assertIn("模拟的审计报告", result)
        self.assertIn("**", result)
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_audit_api_error(self, mock_post):
        # 模拟 API 报错
        mock_post.side_effect = Exception("Network Error")

        result = self.auditor.audit("test content")
        self.assertIn("大脑连接出了点小问题", result)

    def test_no_api_key(self):
        with patch.dict(os.environ, {"MINIMAX_API_KEY": ""}):
            # 重新实例化以触发 key 检查 (或者直接修改实例属性)
            self.auditor.api_key = ""
            result = self.auditor.audit("test content")
            self.assertEqual(result, "API Key 未配置，无法执行审计。")

if __name__ == "__main__":
    unittest.main()
