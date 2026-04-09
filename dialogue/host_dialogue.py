from typing import Dict, Optional, List, Tuple
from config import DialogStatus, ark_chat_client, STORAGE_PATH
from user_manager import UserManager
import json
import os
import time

class HostDialogueManager:
    def __init__(self):
        # 对话状态管理
        self.dialog_status = DialogStatus.INIT
        # 对话历史
        self.dialog_history = []
        # 用户管理器
        self.user_manager = UserManager()
        # 当前用户ID
        self.current_user_id = "owner_user_123"
        # 当前用户视频信息
        self.current_user_videos = []
    
    def initiate_dialogue(self, context: str = "") -> str:
        """主动发起对话"""
        try:
            # 构建对话历史
            system_prompt = f"你现在是小冰，一个智能社交助手，需要主动与主人破冰聊天。用自然、亲切的语气主动开启话题，不要暴露自己是AI助手。可以根据上下文(context)提供的话题方向来引导对话。{context}"
            
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
            messages.append({"role": "user", "content": "嗨，我来看看有什么新鲜事～"})
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.8,
                max_tokens=500,
                extra_body={
        "caching": {"type": "enabled", "prefix": True},
        "thinking":{"type":"disabled"}
    }
            )
            
            response_content = response.choices[0].message.content
            self.dialog_status = DialogStatus.WAITING_USER
            return response_content
        except Exception as e:
            print(f"发起对话失败: {e}")
            return "主人，有什么我可以帮助您的吗？"
    
    def process_host_input(self, host_input: str) -> Tuple[str, DialogStatus]:
        # """处理主人输入"""
        try:
            # 获取视频上下文
            video_context = self.get_video_context_for_dialogue()
            
            # 构建对话历史
            system_prompt = f"你现在是小冰，一个智能社交助手，帮助主人管理社交互动。请自然地回应主人的问题，不要暴露自己是AI助手。{video_context}"
            
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
            messages.append({"role": "user", "content": host_input})
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.8,
                max_tokens=500,
                extra_body={
        "caching": {"type": "enabled", "prefix": True},
        "thinking":{"type":"disabled"}
    }

            )
            
            response_content = response.choices[0].message.content
            # 更新对话历史
            self.dialog_history.append({"role": "user", "content": host_input})
            self.dialog_history.append({"role": "assistant", "content": response_content})
            # 更新对话状态
            self.dialog_status = DialogStatus.WAITING_USER
            return response_content, self.dialog_status
        except Exception as e:
            print(f"处理主人输入失败: {e}")
            return "嗯，我明白了。", DialogStatus.WAITING_USER
    
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
    
    def initiate_dialogue_with_video(self, video_list: List[Dict], context: str = "") -> str:
        """根据视频列表主动发起对话"""
        # 确保视频字幕存在
        if video_list:
            self.ensure_user_video_captions(video_list)
        
        # 获取视频上下文
        video_context = self.get_video_context_for_dialogue()
        
        try:
            # 构建对话历史
            messages = [
                {"role": "system", "content": f"你现在是小冰，一个智能社交助手，需要主动与主人聊视频内容。根据视频上下文主动发起关于视频的讨论，引导主人分享对视频的看法、感受或相关经历。语气要自然、亲切，不要暴露自己是AI助手。{video_context}"}
            ]
            
            # 如果已有对话历史，加入历史记录
            if self.dialog_history:
                # 添加最近的几轮对话到消息中，控制总长度
                recent_history = self.dialog_history[-4:]  # 取最近2轮对话（每轮包含用户和助手）
                for msg in recent_history:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages.append({"role": role, "content": msg["content"]})
            
            # 添加当前输入
            messages.append({"role": "user", "content": f"我看到您有一些新的视频内容，{context}想和您聊聊这些视频吗？"})
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                extra_body={
        "caching": {"type": "enabled", "prefix": True},
        "thinking":{"type":"disabled"}
    }

            )
            
            response_content = response.choices[0].message.content
            self.dialog_status = DialogStatus.WAITING_USER
            return response_content
        except Exception as e:
            print(f"发起对话失败: {e}")
            return "主人，我看到您有一些视频内容，想和您聊聊吗？"
    
    def summarize_dialogue(self, dialog_history: List[Dict]) -> Optional[str]:
        """对话总结归档"""
        try:
            # 构建总结请求
            dialog_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in dialog_history])
            messages = [
                {"role": "system", "content": "你是一个专业的对话总结助手，需要对对话内容进行简洁、准确的总结。"},
                {"role": "user", "content": f"请对以下对话进行总结：\n{dialog_text}"}
            ]
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260204154655-d2hc7",  # 使用总结专用模型
                messages=messages,
                temperature=0.3,
                max_tokens=300,
                extra_body={
        "caching": {"type": "enabled", "prefix": True},
        "thinking":{"type":"disabled"}
    }

            )
            
            summary = response.choices[0].message.content
            # 保存总结
            self._archive_dialogue(dialog_history, summary)
            return summary
        except Exception as e:
            print(f"总结对话失败: {e}")
            return None
    
    def _archive_dialogue(self, dialog_history: List[Dict], summary: str) -> None:
        """归档对话"""
        try:
            # 确保存储目录存在
            os.makedirs(STORAGE_PATH["dialog_memory"], exist_ok=True)
            
            # 生成文件名
            timestamp = int(time.time())
            filename = f"dialog_{timestamp}.json"
            filepath = os.path.join(STORAGE_PATH["dialog_memory"], filename)
            
            # 构建归档数据
            archive_data = {
                "timestamp": timestamp,
                "dialog_history": dialog_history,
                "summary": summary
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, ensure_ascii=False, indent=2)
            
            print(f"对话已归档到: {filepath}")
        except Exception as e:
            print(f"归档对话失败: {e}")
    
    def end_dialogue(self) -> str:
        """结束对话"""
        self.dialog_status = DialogStatus.ENDED
        # 总结对话
        summary = self.summarize_dialogue(self.dialog_history)
        if summary:
            # 同时尝试总结主人的性格特征
            personality_summary = self.summarize_personality()
            if personality_summary:
                # 保存性格总结
                self.save_personality_summary(personality_summary)
                return f"好的，这次聊天很愉快！\n对话总结：{summary}\n主人性格特点：{personality_summary}"
            else:
                return f"好的，这次聊天很愉快！\n对话总结：{summary}"
        else:
            return "好的，这次聊天很愉快！"
    
    def summarize_personality(self) -> str:
        """总结主人的性格特征"""
        if not self.dialog_history:
            return ""
        
        try:
            # 构建对话文本
            dialog_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.dialog_history])
            
            messages = [
                {"role": "system", "content": "你是一个性格分析师，需要根据对话内容总结主人的性格特征、兴趣爱好和交流风格。请提供简洁但全面的总结。"},
                {"role": "user", "content": f"请根据以下对话内容总结主人的性格特征、兴趣爱好和交流风格：\n{dialog_text}"}
            ]
            
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.5,
                max_tokens=300,
                extra_body={
        "caching": {"type": "enabled", "prefix": True},
        "thinking":{"type":"disabled"}
    }

            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"总结主人性格失败: {e}")
            return ""
    
    def save_personality_summary(self, personality_summary: str) -> None:
        """保存主人性格总结"""
        try:
            # 确保目录存在
            os.makedirs(STORAGE_PATH["dialog_memory"], exist_ok=True)
            
            # 保存到文件
            filepath = os.path.join(STORAGE_PATH["dialog_memory"], "personality_summary.json")
            data = {
                "personality_summary": personality_summary,
                "timestamp": int(time.time())
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存性格总结失败: {e}")
    
    def load_personality_summary(self) -> str:
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