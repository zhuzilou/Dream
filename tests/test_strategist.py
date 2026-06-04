import unittest
import os
import sys
import pandas as pd
from unittest.mock import MagicMock

# 将 src 目录添加到路径
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from strategist.trade_advisor import TradeAdvisor

class TestStrategist(unittest.TestCase):
    def setUp(self):
        self.advisor = TradeAdvisor()
        # 构造足够的数据量 (>=20行) 以满足 MA 计算要求
        self.mock_hist = pd.DataFrame({
            'close': [10.0] * 30,
            'high': [11.0] * 30,
            'low': [9.0] * 30
        })

    def test_generate_plan_buy_signal(self):
        ai_analysis = {
            "sentiment_score": 8,
            "summary": "重大利好"
        }
        current_price = 10.0
        
        plan = self.advisor.generate_plan("300750", current_price, self.mock_hist, ai_analysis)
        
        self.assertIsNotNone(plan)
        self.assertIn("买入", plan["action"])
        self.assertIsNotNone(plan["buy_price"])

    def test_generate_plan_wait_signal(self):
        ai_analysis = {
            "sentiment_score": 2, 
            "summary": "普通新闻"
        }
        current_price = 10.0
        
        plan = self.advisor.generate_plan("300750", current_price, self.mock_hist, ai_analysis)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["action"], "观望")

if __name__ == "__main__":
    unittest.main()
