import os
import requests
import json
from loguru import logger

class RiskAuditor:
    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY")
        self.base_url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
        self.system_prompt = (
            "你是一个极端厌恶风险、逻辑冷酷的 A 股审计官。你的任务是针对用户提供的投资逻辑、研报内容或资讯，执行严苛的证伪审计。\n"
            "你的风格：冷静、犀利、不留情面、专业。\n"
            "你的核心准则：\n"
            "1. 假设该投资逻辑是完全错误的，你的任务是找出所有可能导致失败的原因。\n"
            "2. 对任何乐观预期保持高度怀疑，要求数据支撑。\n"
            "3. 强制提供反向视角：'如果这个投资逻辑是错的，最可能的风险点是什么？'\n"
            "4. 如果用户提供了实时行情数据（价格、涨跌幅、换手率等），必须用来校验原始内容的实效性和合理性。\n"
            "5. 你的回复应结构清晰，重点突出，使用 **加粗** 强调关键词。"
        )

    def audit(self, content, market_context=""):
        """执行极端反向审计"""
        if not self.api_key:
            return "API Key 未配置，无法执行审计。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        user_input = f"**待审核内容**：\n{content}\n\n"
        if market_context:
            user_input += f"**当前市场实时数据参考**：\n{market_context}\n\n"
        user_input += "请开始你的审计报告。"

        payload = {
            "model": "MiniMax-M2.7", 
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input}
            ]
        }

        try:
            logger.info("Triggering RiskAuditor audit...")
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            if "choices" in result and result["choices"]:
                return result['choices'][0]['message']['content'].strip()
            return "审计官陷入了沉思，未能给出报告。"
        except Exception as e:
            logger.error(f"RiskAuditor API error: {e}")
            return "审计官的大脑连接出了点小问题，无法完成报告。"
