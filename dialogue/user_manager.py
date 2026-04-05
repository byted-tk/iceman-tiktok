import json
import os
import re
from typing import Dict, List, Optional
from vlm import VLMManager

class UserManager:
    def __init__(self):
        self.vlm_manager = VLMManager()
        # 确保用户视频字幕目录存在
        self.user_captions_dir = "./dataset/user_video_captions"
        os.makedirs(self.user_captions_dir, exist_ok=True)
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的特殊字符以避免路径错误"""
        # 替换可能导致路径问题的特殊字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除或替换控制字符
        sanitized = ''.join(c for c in sanitized if ord(c) >= 32)
        # 限制文件名长度
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized
    
    def get_user_by_id(self, user_open_id: str) -> Optional[Dict]:
        """根据ID获取用户信息"""
        # 从用户数据文件中查找用户
        user_data_file = "./dataset/user_data.json"
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查数据结构，可能是 [{"open_id": "..."}, ...] 或者直接是数组
                if isinstance(data, dict) and 'users' in data:
                    users = data['users']
                elif isinstance(data, list):
                    users = data
                else:
                    # 如果数据结构不符合预期，直接返回None
                    return None
                
                if isinstance(users, list):
                    for user in users:
                        if isinstance(user, dict) and user.get('open_id') == user_open_id:
                            return user
        return None
    
    def has_video_caption(self, user_open_id: str, video_id: str) -> bool:
        """检查用户是否有视频字幕"""
        user_dir = os.path.join(self.user_captions_dir, user_open_id)
        if not os.path.exists(user_dir):
            return False
        
        # 清理video_id中的特殊字符以避免文件路径错误
        safe_video_id = self._sanitize_filename(video_id)
        caption_file = os.path.join(user_dir, f"{safe_video_id}_caption.json")
        return os.path.exists(caption_file)
    
    def get_video_caption(self, user_open_id: str, video_id: str) -> str:
        """获取用户视频字幕"""
        user_dir = os.path.join(self.user_captions_dir, user_open_id)
        
        # 清理video_id中的特殊字符以避免文件路径错误
        safe_video_id = self._sanitize_filename(video_id)
        caption_file = os.path.join(user_dir, f"{safe_video_id}_caption.json")
        
        if os.path.exists(caption_file):
            with open(caption_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('caption', '')
        return ''
    
    def save_video_caption(self, user_open_id: str, video_id: str, caption: str) -> bool:
        """保存用户视频字幕"""
        user_dir = os.path.join(self.user_captions_dir, user_open_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # 清理video_id中的特殊字符以避免文件路径错误
        safe_video_id = self._sanitize_filename(video_id)
        caption_file = os.path.join(user_dir, f"{safe_video_id}_caption.json")
        
        try:
            with open(caption_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'video_id': video_id,
                    'caption': caption,
                    'user_id': user_open_id
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存视频字幕失败: {e}")
            return False
    
    def ensure_video_caption_exists(self, user_open_id: str, video_info: Dict) -> str:
        """确保用户视频字幕存在，如果不存在则自动生成"""
        video_id = video_info.get('item_id', '')
        
        # 检查是否已有字幕
        if self.has_video_caption(user_open_id, video_id):
            caption = self.get_video_caption(user_open_id, video_id)
            print(f"用户 {user_open_id} 的视频 {video_id} 字幕已存在")
            return caption
        else:
            print(f"用户 {user_open_id} 的视频 {video_id} 字幕不存在，正在生成...")
            
            # 使用VLM生成字幕
            caption = self.vlm_manager.generate_caption(video_info)
            
            if caption:
                # 保存字幕
                self.save_video_caption(user_open_id, video_id, caption)
                print(f"已为用户 {user_open_id} 生成并保存视频 {video_id} 的字幕")
            else:
                print(f"为用户 {user_open_id} 生成视频 {video_id} 字幕失败")
                # 返回一个默认值
                caption = "视频内容描述不可用"
                
            return caption
    
    def batch_ensure_captions(self, user_open_id: str, video_list: List[Dict]) -> List[Dict]:
        """批量确保视频字幕存在"""
        updated_videos = []
        for video in video_list:
            # 添加字幕信息到视频对象
            caption = self.ensure_video_caption_exists(user_open_id, video)
            video_copy = video.copy()
            video_copy['caption'] = caption
            updated_videos.append(video_copy)
        return updated_videos