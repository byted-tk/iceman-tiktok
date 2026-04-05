import json
import os
from typing import Dict, List, Optional
from config import ark_chat_client

class PrivacyManager:
    def __init__(self):
        # 加载隐私规则
        self.privacy_rules = self._load_privacy_rules()
    
    def _load_privacy_rules(self) -> Dict:
        """加载隐私规则"""
        # 默认隐私规则
        default_rules = {
            "personal_info_protection": [
                "姓名",
                "电话",
                "地址", 
                "身份证",
                "银行账户",
                "私人行程"
            ],
            "response_templates": {
                "safe_response": "关于这个问题，我需要保护个人隐私，不能透露具体信息。",
                "redirect_response": "这很有趣，我们可以聊聊其他方面。",
                "general_response": "我了解您的兴趣，但为了保护隐私，我只能提供一般性的信息。"
            }
        }
        return default_rules
    
    def protect_privacy(self, text: str, user_type: str = "visitor") -> str:
        """保护隐私信息"""
        if user_type != "visitor":
            return text  # 只对访客隐藏隐私信息
        
        protected_text = text
        # 检查是否包含隐私信息
        for info_type in self.privacy_rules["personal_info_protection"]:
            if info_type in protected_text:
                # 替换为通用响应
                protected_text = self.privacy_rules["response_templates"]["safe_response"]
                break
        
        return protected_text
    
    def generate_owner_representative_response(self, query: str, owner_context: str = "") -> str:
        """生成代表主人的响应"""
        try:
            # 构建提示词，让AI以主人的视角回答，但保护隐私
            prompt = f"""
            你现在是一个善于社交的真人，需要代替主人回答访客的问题，语气要自然亲切，不要暴露身份是AI助手。
            
            访客的问题：{query}
            
            请根据以下原则回答：
            1. 用自然、口语化的语气回应，就像真人在聊天
            2. 不要提及自己是AI助手或机器人
            3. 保护主人的隐私信息，不透露敏感内容（如地址、电话等）
            4. 如果涉及隐私问题，巧妙地转移话题或给出一般性回答
            5. 保持友善、真实的互动感觉
            6. 可以分享一些普遍的观点或经验，但不要编造具体的个人信息
            
            举例来说，如果访客问'你住在哪里？'，可以回答'我在一座美丽的城市生活，很喜欢这里的生活节奏'而不是直接拒绝回答。
            
            请给出自然的回应：
            """
            
            messages = [
                {"role": "system", "content": "你是一个善于社交的真人，需要代替主人回答访客的问题，语气要自然亲切，不要暴露身份是AI助手。"},
                {"role": "user", "content": prompt}
            ]
            
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.8,  # 提高温度以获得更自然的回应
                max_tokens=300
            )
            
            raw_response = response.choices[0].message.content
            
            # 进一步处理以确保隐私保护
            protected_response = self.protect_privacy(raw_response, "visitor")
            
            return protected_response
        except Exception as e:
            print(f"生成主人代表响应失败: {e}")
            return "不错的问题！每个人都会有自己独特的喜好，这正是生活的魅力所在。"

    def is_privacy_sensitive(self, query: str) -> bool:
        """判断查询是否涉及隐私敏感内容"""
        sensitive_keywords = [
            "电话", "手机", "联系方式", "住址", "家庭", "私人", "秘密", 
            "收入", "财务", "密码", "证件", "身份证", "银行卡", 
            "行程", "约会", "私人信息", "隐私"
        ]
        
        for keyword in sensitive_keywords:
            if keyword in query:
                return True
        return False