from typing import Optional, Dict
from config import ark_chat_client
import json
import os

class VLMManager:
    def __init__(self):
        # 视频caption存储路径
        self.caption_storage = "./dataset/video_captions.json"
        # 加载现有caption
        self.captions = self._load_captions()
    
    def _load_captions(self) -> Dict:
        """加载现有的视频caption"""
        try:
            if os.path.exists(self.caption_storage):
                with open(self.caption_storage, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载caption失败: {e}")
            return {}
    
    def _save_captions(self) -> None:
        """保存视频caption"""
        try:
            with open(self.caption_storage, 'w', encoding='utf-8') as f:
                json.dump(self.captions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存caption失败: {e}")
    
    def generate_caption(self, video_info: Dict) -> Optional[str]:
        """为视频生成caption"""
        try:
            video_id = video_info.get("item_id")
            title = video_info.get("title", "")
            share_url = video_info.get("share_url", "")
            cover = video_info.get("cover", "")
            
            # 检查是否已有caption
            if video_id in self.captions:
                print(f"视频 {video_id} 已有caption: {self.captions[video_id]}")
                return self.captions[video_id]
            
            # 创建详细的视频描述提示
            prompt = f"""
            请根据以下视频信息生成详细的内容描述：
            
            视频标题: {title}
            分享链接: {share_url}
            
            请提供以下方面的描述：
            1. 视频的主要内容和主题
            2. 视频中的主要对象或人物
            3. 视频的场景或背景
            4. 视频的情感或氛围
            5. 视频可能使用的音乐或音效
            6. 视频的风格特点
            7. 视频的目标受众或适用场景
            
            请用中文生成一段详细、准确且生动的视频描述，长度约100-200字。
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的视频内容描述助手，能够根据视频信息生成准确、详细且富有吸引力的视频内容描述。"},
                {"role": "user", "content": prompt}
            ]
            
            # 调用OpenAI API
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",  # 使用多模态模型
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            caption = response.choices[0].message.content
            
            # 存储caption
            self.captions[video_id] = caption
            self._save_captions()
            
            print(f"为视频 {video_id} 生成caption: {caption}")
            return caption
        except Exception as e:
            print(f"生成caption失败: {e}")
            return None
    
    def get_caption(self, video_id: str) -> Optional[str]:
        """获取视频的caption"""
        return self.captions.get(video_id, None)
    
    def batch_generate_captions(self, video_items: list) -> Dict:
        """批量为视频生成caption"""
        results = {}
        for item in video_items:
            video_id = item.get("item_id")
            if video_id:
                caption = self.generate_caption(item)
                results[video_id] = caption
        return results
    
    def process_api_response(self, api_response: Dict) -> Dict:
        """处理API响应并生成caption"""
        try:
            # 从API响应中提取视频列表
            video_list = api_response.get('data', {}).get('data', {}).get('list', [])
            print(f"从API响应中提取到 {len(video_list)} 个视频")
            
            # 为每个视频生成caption
            results = self.batch_generate_captions(video_list)
            
            # 为每个视频添加caption
            for video in video_list:
                video_id = video.get("item_id")
                if video_id and video_id in results:
                    video['caption'] = results[video_id]
            
            return {
                "processed_videos": video_list,
                "captions": results
            }
        except Exception as e:
            print(f"处理API响应失败: {e}")
            return {"processed_videos": [], "captions": {}}
    
    def get_video_summary(self, video_info: Dict) -> Optional[str]:
        """获取视频摘要"""
        try:
            video_id = video_info.get("item_id")
            title = video_info.get("title", "")
            
            # 如果已有完整caption，则生成摘要
            existing_caption = self.get_caption(video_id)
            if existing_caption:
                prompt = f"""
                请将以下视频描述压缩成一句话摘要：
                
                {existing_caption}
                
                请用简洁的语言总结视频的核心内容，不超过50个字。
                """
                
                messages = [
                    {"role": "system", "content": "你是一个专业的文本摘要助手，能够将长文本压缩成简洁的摘要。"},
                    {"role": "user", "content": prompt}
                ]
                
                response = ark_chat_client.chat.completions.create(
                    model="ep-20260204154655-d2hc7",  # 使用总结专用模型
                    messages=messages,
                    temperature=0.3,
                    max_tokens=100
                )
                
                return response.choices[0].message.content
            
            # 如果没有完整caption，直接基于标题生成摘要
            if title:
                prompt = f"请为以下视频标题生成一句话摘要：{title}"
                
                messages = [
                    {"role": "system", "content": "你是一个专业的文本摘要助手，能够将长文本压缩成简洁的摘要。"},
                    {"role": "user", "content": prompt}
                ]
                
                response = ark_chat_client.chat.completions.create(
                    model="ep-20260204154655-d2hc7",  # 使用总结专用模型
                    messages=messages,
                    temperature=0.3,
                    max_tokens=100
                )
                
                return response.choices[0].message.content
            
            return None
        except Exception as e:
            print(f"生成视频摘要失败: {e}")
            return None
    
    def update_video_metadata(self, video_info: Dict) -> Dict:
        """更新视频元数据，包括caption和summary"""
        try:
            # 生成完整caption
            caption = self.generate_caption(video_info)
            if caption:
                video_info['caption'] = caption
            
            # 生成摘要
            summary = self.get_video_summary(video_info)
            if summary:
                video_info['summary'] = summary
            
            return video_info
        except Exception as e:
            print(f"更新视频元数据失败: {e}")
            return video_info