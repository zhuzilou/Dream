import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# 将 src 目录添加到路径
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from analyst.llm_engine import Analyst

class TestAnalyst(unittest.TestCase):
    def setUp(self):
        os.environ["MINIMAX_API_KEY"] = "test_key"
        self.analyst = Analyst()

    @patch("requests.post")
    def test_analyze_news_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"sentiment_score": 7.5, "summary": "利好"}'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        result = self.analyst.analyze_news("标题", "内容")
        self.assertEqual(result["sentiment_score"], 7.5)

if __name__ == "__main__":
    unittest.main()
