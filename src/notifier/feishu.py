import os
import requests
import json
from loguru import logger

class FeishuBot:
    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.token = None

    def get_tenant_access_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                self.token = data.get("tenant_access_token")
                return self.token
            else:
                logger.error(f"Failed to get Feishu token: {data.get('msg')}")
        except Exception as e:
            logger.error(f"Error fetching Feishu token: {e}")
        return None

    def send_text_message(self, receive_id, text, receive_id_type="open_id"):
        """
        发送纯文本消息。
        """
        if not self.token:
            self.get_tenant_access_token()
            
        if not self.token:
            return False

        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text})
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            data = response.json()
            # 如果 token 过期，清除并重试一次
            if data.get("code") == 99991663:
                logger.warning("Token expired, refreshing and retrying...")
                self.token = None
                return self.send_text_message(receive_id, text, receive_id_type)
                
            if data.get("code") == 0:
                logger.info("Feishu message sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Feishu message: {data}")
        except Exception as e:
            logger.error(f"Error sending Feishu message: {e}")
        return False

    def get_message_content(self, message_id):
        """获取指定消息的内容（支持文本和富文本）"""
        if not self.token:
            self.get_tenant_access_token()
        
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            if data.get("code") == 0:
                items = data.get("data", {}).get("items", [])
                if items:
                    msg_type = items[0].get("msg_type")
                    content_str = items[0].get("body", {}).get("content", "{}")
                    content = json.loads(content_str)
                    
                    if msg_type == "text":
                        return content.get("text", "")
                    elif msg_type == "post":
                        try:
                            text_parts = []
                            post_data = content.get("post", content) # 兼容直接包含 title/content 的格式
                            
                            # 获取内容列表
                            content_rows = []
                            if "zh_cn" in post_data:
                                content_rows = post_data["zh_cn"].get("content", [])
                            elif "content" in post_data and isinstance(post_data["content"], list):
                                content_rows = post_data["content"]
                            else:
                                # 尝试遍历所有 key 寻找 content
                                for val in post_data.values():
                                    if isinstance(val, dict) and "content" in val:
                                        content_rows = val.get("content", [])
                                        break
                            
                            for row in content_rows:
                                for element in row:
                                    tag = element.get("tag")
                                    if tag == "text":
                                        text_parts.append(element.get("text", ""))
                                    elif tag == "a":
                                        text_parts.append(element.get("text", ""))
                                    elif tag == "at":
                                        text_parts.append(element.get("at_name", ""))
                            
                            result = "".join(text_parts).strip()
                            if not result:
                                logger.debug(f"Post content parsed as empty. Original: {content_str}")
                            return result
                        except Exception as e:
                            logger.error(f"Post parse error: {e}. Content: {content_str}")
                            return "[富文本内容解析失败]"
                    elif msg_type == "interactive":
                        return self._parse_interactive_card(content)
                    return f"[暂不支持的消息类型: {msg_type}]"
                else:
                    logger.warning(f"No message found for ID: {message_id}")
            elif data.get("code") == 99991663:
                logger.warning("Token expired while fetching message content, refreshing...")
                self.token = None
                return self.get_message_content(message_id)
            else:
                logger.error(f"Failed to fetch message content: Code={data.get('code')}, Msg={data.get('msg')}")
        except Exception as e:
            logger.error(f"Error fetching message content: {e}")
        return None

    def send_post_message(self, receive_id, title, content_list, receive_id_type="open_id"):
        """
        发送富文本消息 (Post)
        content_list: [['text', 'line1'], ['text', 'line2']]
        """
        if not self.token:
            self.get_tenant_access_token()
            
        if not self.token:
            return False

        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.token}"
        }
        
        # 确保 title 没有换行符且长度符合限制 (100字符)
        safe_title = str(title).replace("\n", " ").strip()[:100]
        
        # 构造内容
        rows = []
        for item in content_list:
            if len(item) >= 2 and item[1]:
                # 支持将文本内的换行符拆分为多行
                lines = str(item[1]).split("\n")
                for line in lines:
                    line = line.strip()
                    if line:
                        rows.append([{"tag": "text", "text": line}])
        
        if not rows:
            logger.warning("Post content is empty, skipping.")
            return False

        post_content = {
            "zh_cn": {
                "title": safe_title,
                "content": rows
            }
        }
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "post",
            "content": json.dumps(post_content)
        }
        
        try:
            # 调试日志：记录发送的消息结构（截断长内容）
            debug_content = payload['content'][:200] + "..." if len(payload['content']) > 200 else payload['content']
            logger.debug(f"Sending Feishu post to {receive_id}: {debug_content}")
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            data = response.json()
            if data.get("code") == 0:
                logger.info("Feishu post message sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Feishu post: {data}")
                # 尝试退化为普通文本发送
                fallback_text = f"【{safe_title}】\n" + "\n".join([str(item[1]) for item in content_list if len(item) >= 2])
                return self.send_text_message(receive_id, fallback_text, receive_id_type=receive_id_type)
        except Exception as e:
            logger.error(f"Error sending Feishu post: {e}")
        return False

    def send_interactive_message(self, receive_id, title, markdown_text, receive_id_type="open_id"):
        """
        发送消息卡片 (Interactive)，原生支持 Markdown
        """
        if not self.token:
            self.get_tenant_access_token()
            
        if not self.token:
            return False

        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.token}"
        }
        
        card_content = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": markdown_text
                }
            ]
        }
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            data = response.json()
            if data.get("code") == 0:
                logger.info("Feishu card message sent successfully.")
                return True
            elif data.get("code") == 99991663:
                self.token = None
                return self.send_interactive_message(receive_id, title, markdown_text, receive_id_type)
            else:
                logger.error(f"Failed to send Feishu card: Code={data.get('code')}, Msg={data.get('msg')}")
                # 回退到 Text
                return self.send_text_message(receive_id, f"【{title}】\n{markdown_text}", receive_id_type)
        except Exception as e:
            logger.error(f"Error sending Feishu card: {e}")
        return False

    def _parse_interactive_card(self, card_data):
        """解析交互式卡片，确保 Header 优先级最高"""
        results = []
        # 1. 优先提取 Header (权重最高)
        header = card_data.get("header", {})
        header_text = self._recursive_extract_text(header)
        if header_text:
            results.append(f"【标题】{header_text}")
        
        # 2. 提取 Elements (主要内容)
        elements = card_data.get("elements", [])
        elements_text = self._recursive_extract_text(elements)
        if elements_text:
            results.append(elements_text)
            
        # 3. 如果没抓到特定结构，兜底全量解析
        if not results:
            return self._recursive_extract_text(card_data)
            
        return "\n".join(results).strip()

    def _recursive_extract_text(self, obj, depth=0):
        """递归提取文本，支持 i18n、多标签，并有深度保护"""
        if depth > 10:  # 深度保护
            return ""
            
        text_bits = []
        if isinstance(obj, dict):
            # 1. 优先处理 i18n
            if "i18n" in obj:
                zh_cn = obj["i18n"].get("zh_cn", "")
                if zh_cn:
                    text_bits.append(zh_cn)
                else:
                    # 尝试其他语言或兜底
                    for lang_val in obj["i18n"].values():
                        if isinstance(lang_val, str):
                            text_bits.append(lang_val)
                            break
            
            # 2. 处理标准文本标签
            tag = obj.get("tag")
            if tag in ["plain_text", "lark_md", "markdown"]:
                content = obj.get("content", "")
                if content:
                    text_bits.append(content)
            
            # 3. 递归遍历所有 key (排除已处理的 tag/content/i18n)
            for key, value in obj.items():
                if key not in ["tag", "content", "i18n"]:
                    text_bits.append(self._recursive_extract_text(value, depth + 1))
                    
        elif isinstance(obj, list):
            for item in obj:
                text_bits.append(self._recursive_extract_text(item, depth + 1))
        
        return " ".join([t for t in text_bits if t]).strip()
