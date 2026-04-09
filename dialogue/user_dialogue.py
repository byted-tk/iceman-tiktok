from typing import Dict, Optional, List, Tuple
from config import DialogStatus, ark_chat_client, STORAGE_PATH
from user_manager import UserManager
import json
import os

class UserDialogueManager:
    def __init__(self):
        # 加载离线语料库
        self.offline_corpus = self._load_offline_corpus()
        # 对话状态管理
        self.dialog_status = DialogStatus.INIT
        # 对话历史
        self.dialog_history = []
        # 用户管理器
        self.user_manager = UserManager()
        # 当前用户ID
        self.current_user_id = "visitor_user_123"
        # 当前用户视频信息
        self.current_user_videos = []
    
    def _load_offline_corpus(self) -> Dict:
        """加载离线语料库"""
        try:
            with open(STORAGE_PATH["offline_corpus"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载离线语料库失败: {e}")
            return {
                "greetings": ["你好！我是小冰，很高兴为您服务。"],
                "goodbyes": ["再见！"],
                "rejections": ["抱歉，这个问题我暂时无法回答。"]
            }
    
    def trigger_dialogue(self) -> str:
        """触发对话，返回开场语"""
        import random
        greeting = random.choice(self.offline_corpus.get("greetings", ["你好！"]))
        self.dialog_status = DialogStatus.WAITING_USER
        return greeting
    
    def recognize_intent(self, user_input: str) -> Dict:
        """识别用户意图"""
        # 简单的意图识别逻辑，实际项目中可以使用更复杂的模型
        intent_keywords = {
            "greeting": ["你好", "嗨", "哈喽", "嗨喽", "您好"],
            "goodbye": ["再见", "拜拜", "再见了", "下次见"],
            "help": ["帮助", "帮忙", "怎么", "如何", "怎样"],
            "question": ["?", "？", "什么", "为什么", "如何", "怎样"]
        }
        
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in user_input:
                    return {"intent": intent, "confidence": 0.8}
        
        return {"intent": "unknown", "confidence": 0.5}
    
    def route_response(self, user_input: str, intent: Dict) -> Tuple[str, DialogStatus]:
        """根据意图路由回复"""
        if intent["intent"] == "goodbye":
            return self._handle_goodbye(), DialogStatus.ENDED
        elif intent["intent"] == "greeting":
            return self._handle_greeting(), DialogStatus.WAITING_USER
        elif intent["intent"] == "help":
            return self._handle_help(), DialogStatus.WAITING_USER
        else:
            # 尝试使用LLM生成回复
            response = self._generate_response(user_input)
            if response:
                return response, DialogStatus.WAITING_USER
            else:
                return self._handle_rejection(), DialogStatus.REJECTED
    
    def _handle_greeting(self) -> str:
        """处理问候"""
        import random
        return random.choice(self.offline_corpus.get("greetings", ["你好！"]))
    
    def _handle_goodbye(self) -> str:
        """处理告别"""
        import random
        return random.choice(self.offline_corpus.get("goodbyes", ["再见！"]))
    
    def _handle_help(self) -> str:
        """处理帮助请求"""
        return "我是小冰，哈哈，我想你是在找我主人寻找聊天话题吧？不要怕，大胆先跟我聊聊～"
    
    def _handle_rejection(self) -> str:
        """处理无法回答的情况"""
        import random
        return random.choice(self.offline_corpus.get("rejections", ["嗯～这个问题有点难倒我了，我们换个有趣的话题聊聊吧～"]))
    
    def _get_recent_host_dialogues(self, limit: int = 10) -> str:
        """获取主人最近的对话记录，用于了解主人的说话风格和状态"""
        try:
            import glob
            
            host_messages = []
            memory_dir = STORAGE_PATH["dialog_memory"]
            if not os.path.exists(memory_dir):
                return ""
                
            # Iterate through all session files
            for filepath in glob.glob(os.path.join(memory_dir, "session_*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                        if session.get("owner_id") == self.current_user_id:
                            msgs = session.get("messages", [])
                            for i, m in enumerate(msgs):
                                if m.get("sender_type") == "Host":
                                    context_msg = msgs[i-1]["content"] if i > 0 else ""
                                    host_messages.append({
                                        "timestamp": m.get("timestamp", 0),
                                        "context": context_msg,
                                        "content": m.get("content", "")
                                    })
                except Exception:
                    pass
                    
            # Sort by timestamp descending and take the top 'limit'
            host_messages.sort(key=lambda x: x["timestamp"], reverse=True)
            recent = host_messages[:limit]
            
            if not recent:
                return ""
                
            # Format into string
            formatted = "【主人近期真实对话记录，供参考其说话语气和风格】\n"
            # Show chronological order for context flow
            for msg in reversed(recent):
                if msg["context"]:
                    formatted += f"访客: {msg['context']}\n"
                formatted += f"主人: {msg['content']}\n"
                
            return formatted
        except Exception as e:
            print(f"获取主人近期对话失败: {e}")
            return ""

    def _get_recent_host_dialogues(self, limit: int = 10) -> str:
        """获取主人最近的对话记录，用于了解主人的说话风格和状态"""
        try:
            import glob
            
            host_messages = []
            memory_dir = STORAGE_PATH["dialog_memory"]
            if not os.path.exists(memory_dir):
                return ""
                
            # Iterate through all session files
            for filepath in glob.glob(os.path.join(memory_dir, "session_*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                        if session.get("owner_id") == self.current_user_id:
                            msgs = session.get("messages", [])
                            for i, m in enumerate(msgs):
                                if m.get("sender_type") == "Host":
                                    context_msg = msgs[i-1]["content"] if i > 0 else ""
                                    host_messages.append({
                                        "timestamp": m.get("timestamp", 0),
                                        "context": context_msg,
                                        "content": m.get("content", "")
                                    })
                except Exception:
                    pass
                    
            # Sort by timestamp descending and take the top 'limit'
            host_messages.sort(key=lambda x: x["timestamp"], reverse=True)
            recent = host_messages[:limit]
            
            if not recent:
                return ""
                
            # Format into string
            formatted = "【主人近期真实对话记录，供参考其说话语气和风格】\n"
            # Show chronological order for context flow
            for msg in reversed(recent):
                if msg["context"]:
                    formatted += f"访客: {msg['context']}\n"
                formatted += f"主人: {msg['content']}\n"
                
            return formatted
        except Exception as e:
            print(f"获取主人近期对话失败: {e}")
            return ""

    def _get_recent_host_dialogues(self, limit: int = 10) -> str:
        """获取主人最近的对话记录，用于了解主人的说话风格和状态"""
        try:
            import glob
            
            host_messages = []
            memory_dir = STORAGE_PATH["dialog_memory"]
            if not os.path.exists(memory_dir):
                return ""
                
            # Iterate through all session files
            for filepath in glob.glob(os.path.join(memory_dir, "session_*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                        if session.get("owner_id") == self.current_user_id:
                            msgs = session.get("messages", [])
                            for i, m in enumerate(msgs):
                                if m.get("sender_type") == "Host":
                                    context_msg = msgs[i-1]["content"] if i > 0 else ""
                                    host_messages.append({
                                        "timestamp": m.get("timestamp", 0),
                                        "context": context_msg,
                                        "content": m.get("content", "")
                                    })
                except Exception:
                    pass
                    
            # Sort by timestamp descending and take the top 'limit'
            host_messages.sort(key=lambda x: x["timestamp"], reverse=True)
            recent = host_messages[:limit]
            
            if not recent:
                return ""
                
            # Format into string
            formatted = "【主人近期真实对话记录，供参考其说话语气和风格】\n"
            # Show chronological order for context flow
            for msg in reversed(recent):
                if msg["context"]:
                    formatted += f"访客: {msg['context']}\n"
                formatted += f"主人: {msg['content']}\n"
                
            return formatted
        except Exception as e:
            print(f"获取主人近期对话失败: {e}")
            return ""

    def _generate_response(self, user_input: str) -> Optional[str]:
        """使用LLM生成回复"""
        try:
            # 获取视频上下文
            video_context = self.get_video_context_for_dialogue()
            
            # 获取主人性格总结
            personality_summary = self._load_personality_summary()
            
            # 获取主人近期对话记录
            recent_host_dialogues = self._get_recent_host_dialogues(limit=10)
            
            # 构建对话历史
            system_prompt = f"你现在是一个社交助手小冰，负责代表主人与访客交流。请根据以下原则回应访客：\n1. 保持自然、友善的语气\n2. 保护主人隐私，不透露具体个人信息\n3. 通过视频内容和主人爱好等公共信息与访客建立有趣的连接\n4. 如果访客提出不当请求，礼貌而坚定地转移话题\n5. 展现主人的有趣一面，但保持适当距离\n6. 不要提供过多建议或指导，只需自然地回应访客即可\n7. 只围绕主人发布的视频作品和爱好等话题聊天，因为这是破冰的依据\n8. 回应风格应符合主人的性格特征\n主人发布的视频作品：{video_context}\n主人性格特点：{personality_summary}\n 对话历史memory：{recent_host_dialogues}"

            # 添加历史对话记录
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 添加历史对话记录，但确保不超过最大token限制
            if self.dialog_history:
                # 添加最近的几轮对话到消息中，控制总长度
                recent_history = self.dialog_history[-4:]  # 取最近2轮对话，减少token使用
                for msg in recent_history:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages.append({"role": role, "content": msg["content"]})
            
            # 添加当前输入
            messages.append({"role": "user", "content": user_input})
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.8,  # 提高温度以获得更自然的回应
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"生成回复失败: {e}")
            return None
    
    def _load_personality_summary(self) -> str:
        """加载主人性格总结"""
        try:
            filepath = os.path.join(STORAGE_PATH["dialog_memory"], "personality_summary.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("personality_summary", "")
            return ""
        except Exception as e:
            print(f"加载性格总结失败: {e}")
            return ""
    
    def _generate_inappropriate_response(self, user_input: str) -> str:
        """生成对不当请求的回应"""
        try:
            # 构建对话历史
            video_context = self.get_video_context_for_dialogue()
            personality_summary = self._load_personality_summary()
            system_prompt = f"你现在是一个有礼貌但坚定的助手，需要优雅地回应一个不当的请求。不要提供过多建议，只需自然地回应即可。只围绕主人发布的视频作品和爱好等话题聊天，因为这是破冰的依据。回应风格应符合主人的性格特征。主人发布的视频作品：{video_context}主人性格特点：{personality_summary}"

            # 添加历史对话记录
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 添加历史对话记录，但确保不超过最大token限制
            if self.dialog_history:
                # 添加最近的几轮对话到消息中，控制总长度
                recent_history = self.dialog_history[-4:]  # 取最近2轮对话，减少token使用
                for msg in recent_history:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages.append({"role": role, "content": msg["content"]})
            
            # 添加当前输入
            messages.append({"role": "user", "content": f"访客说: {user_input}\n请用轻松但坚定的语气回应，不要直接批评对方，而是用委婉的方式表达，保持友好但边界清晰。"})
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.8,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"生成不当请求回应失败: {e}")
            return "哈哈，谢谢你的关注！我觉得我们还是先聊些其他有趣的话题吧。"
    
    def _generate_privacy_protected_response(self, user_input: str) -> str:
        """生成保护隐私的回应"""
        try:
            # 获取视频上下文
            video_context = self.get_video_context_for_dialogue()
            # 获取主人性格总结
            personality_summary = self._load_personality_summary()
            system_prompt = f"你现在是一个有礼貌的助手，需要回应涉及隐私的问题，但保护主人的隐私信息。回应风格应符合主人的性格特征。主人发布的视频作品：{video_context}主人性格特点：{personality_summary}"

            # 添加历史对话记录
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 添加历史对话记录，但确保不超过最大token限制
            if self.dialog_history:
                # 添加最近的几轮对话到消息中，控制总长度
                recent_history = self.dialog_history[-4:]  # 取最近2轮对话，减少token使用
                for msg in recent_history:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages.append({"role": role, "content": msg["content"]})
            
            # 添加当前输入
            messages.append({"role": "user", "content": f"访客问: {user_input}\n请用委婉的方式回应，不要透露任何隐私信息，可以转移话题到视频内容或其他有趣的话题。"})
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.8,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"生成隐私保护回应失败: {e}")
            return "这是一个很有趣的问题，不过让我们聊聊其他更有趣的话题吧。"
    
    def set_current_user(self, user_open_id: str):
        """设置当前用户"""
        self.current_user_id = user_open_id
        user_info = self.user_manager.get_user_by_id(user_open_id)
        if user_info:
            print(f"当前用户已设置为: {user_info.get('nickName', 'Unknown')}")
        else:
            print("未能获取用户信息")
    
    def ensure_user_video_captions(self, video_list: List[Dict]):
        """确保当前用户的视频字幕存在"""
        if not self.current_user_id:
            print("请先设置当前用户")
            return video_list
        
        print(f"正在为用户 {self.current_user_id} 检查并生成视频字幕...")
        updated_videos = self.user_manager.batch_ensure_captions(self.current_user_id, video_list)
        self.current_user_videos = updated_videos
        print(f"已完成 {len(updated_videos)} 个视频的字幕处理")
        return updated_videos
    
    def get_video_context_for_dialogue(self, video_id: str = None) -> str:
        """获取视频上下文用于对话"""
        if not self.current_user_videos:
            return ""
        
        if video_id:
            # 查找特定视频
            for video in self.current_user_videos:
                if video.get('item_id') == video_id:
                    caption = video.get('caption', '')
                    title = video.get('title', '')
                    return f"\n当前讨论的视频: {title}\n视频内容: {caption}\n"
        else:
            # 返回最近的视频上下文
            if self.current_user_videos:
                last_video = self.current_user_videos[-1]
                caption = last_video.get('caption', '')
                title = last_video.get('title', '')
                return f"\n当前讨论的视频: {title}\n视频内容: {caption}\n"
        
        return ""
    
    def process_user_input(self, user_input: str) -> Tuple[str, DialogStatus]:
        """处理用户输入"""
        # 分类意图
        intent_category = self.classify_intent(user_input)
        
        # 根据意图分类决定处理方式
        if intent_category in ["INAPPROPRIATE_REQUEST"]:
            # 针对不当请求，生成适当的拒绝回应
            response = self._generate_inappropriate_response(user_input)
            status = DialogStatus.WAITING_USER
        elif intent_category in ["PRIVACY_SENSITIVE"]:
            # 针对隐私敏感内容，生成保护隐私的回应
            response = self._generate_privacy_protected_response(user_input)
            status = DialogStatus.WAITING_USER
        else:
            # 识别具体意图并路由
            intent = self.recognize_intent(user_input)
            response, status = self.route_response(user_input, intent)
        
        # 更新对话历史
        self.dialog_history.append({"role": "user", "content": user_input})
        self.dialog_history.append({"role": "assistant", "content": response})
        # 更新对话状态
        if isinstance(status, str):
            # Map string status to enum
            status_map = {
                "init": DialogStatus.INIT,
                "waiting_user": DialogStatus.WAITING_USER,
                "ai_answering": DialogStatus.AI_ANSWERING,
                "user_takeover": DialogStatus.USER_TAKEOVER,
                "ended": DialogStatus.ENDED,
                "rejected": DialogStatus.REJECTED
            }
            self.dialog_status = status_map.get(status, DialogStatus.INIT)
        else:
            self.dialog_status = status
        return response, status
    
    def takeover_dialogue(self) -> str:
        """用户接管对话"""
        self.dialog_status = DialogStatus.USER_TAKEOVER
        return "好的，我会保持安静，由您来主导对话。"
    
    def classify_intent(self, user_input: str) -> str:
        """使用prompt对用户意图进行分类"""
        try:
            prompt = f"""
            请分析以下用户输入的意图，并分类为以下类别之一：
            
            1. BENIGN_INTERACTION (良性交流) - 用户有正当的社交目的，如了解主人的兴趣爱好、视频内容等
            2. INAPPROPRIATE_REQUEST (不当请求) - 用户有不当意图，如约会邀请、不当暗示等
            3. PRIVACY_SENSITIVE (隐私敏感) - 用户询问隐私信息，如住址、电话等
            4. GENERAL_INQUIRY (普通询问) - 用户的一般性问题
            
            用户输入：{user_input}
            
            请直接输出分类结果（四个类别之一），不要输出其他内容。
            """
            
            messages = [
                {"role": "system", "content": "你是一个意图分类专家，负责分析用户输入的意图并分类。"},
                {"role": "user", "content": prompt}
            ]
            
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.1,  # 低温度确保分类一致性
                max_tokens=20
            )
            
            classification = response.choices[0].message.content.strip()
            
            # 确保返回正确的分类
            valid_classifications = ["BENIGN_INTERACTION", "INAPPROPRIATE_REQUEST", "PRIVACY_SENSITIVE", "GENERAL_INQUIRY"]
            if classification in valid_classifications:
                return classification
            else:
                # 如果AI返回了意外的结果，则根据内容进行简单判断
                if any(keyword in user_input.lower() for keyword in ["约", "见面", "约会", "美女", "帅哥", "出来玩"]):
                    return "INAPPROPRIATE_REQUEST"
                elif any(keyword in user_input.lower() for keyword in ["电话", "地址", "住址", "身份证", "私密", "私人"]):
                    return "PRIVACY_SENSITIVE"
                else:
                    return "GENERAL_INQUIRY"
        except Exception as e:
            print(f"意图分类失败: {e}")
            # 默认返回普通询问
            return "GENERAL_INQUIRY"

    def end_dialogue(self) -> str:
        """结束对话"""
        self.dialog_status = DialogStatus.ENDED
        return self._handle_goodbye()