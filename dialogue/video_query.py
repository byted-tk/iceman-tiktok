from typing import Dict, Optional, List
import requests
import json
import os

class VideoQueryManager:
    def __init__(self):
        # API endpoint
        self.api_url = "https://open.douyin.com/api/apps/v1/video/query/"
    
    def query_videos(self, access_token: str, open_id: str, item_ids: List[str]) -> Optional[Dict]:
        """查询视频数据"""
        try:
            headers = {
                "access-token": access_token,
                "content-type": "application/json"
            }
            
            params = {
                "open_id": open_id
            }
            
            data = {
                "item_ids": item_ids
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                params=params,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API请求失败: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            print(f"查询视频失败: {e}")
            return None
    
    def load_mock_response(self) -> Optional[Dict]:
        """加载模拟API响应"""
        try:
            mock_file = "./dataset/mock_api_response.json"
            if os.path.exists(mock_file):
                with open(mock_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print("模拟API响应文件不存在")
                return None
        except Exception as e:
            print(f"加载模拟响应失败: {e}")
            return None
    
    def process_video_data(self, video_data: Dict) -> List[Dict]:
        """处理视频数据"""
        try:
            video_list = video_data.get('data', {}).get('data', {}).get('list', [])
            print(f"获取到 {len(video_list)} 个视频数据")
            return video_list
        except Exception as e:
            print(f"处理视频数据失败: {e}")
            return []
from typing import Dict, Optional, List
import requests
import json
import os

class VideoQueryManager:
    def __init__(self):
        # API endpoint
        self.api_url = "https://open.douyin.com/api/apps/v1/video/query/"
    
    def query_videos(self, access_token: str, open_id: str, item_ids: List[str]) -> Optional[Dict]:
        """查询视频数据"""
        try:
            headers = {
                "access-token": access_token,
                "content-type": "application/json"
            }
            
            params = {
                "open_id": open_id
            }
            
            data = {
                "item_ids": item_ids
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                params=params,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API请求失败: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            print(f"查询视频失败: {e}")
            return None
    
    def load_mock_response(self) -> Optional[Dict]:
        """加载模拟API响应"""
        try:
            mock_file = "./dataset/mock_api_response.json"
            if os.path.exists(mock_file):
                with open(mock_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print("模拟API响应文件不存在")
                return None
        except Exception as e:
            print(f"加载模拟响应失败: {e}")
            return None
    
    def process_video_data(self, video_data: Dict) -> List[Dict]:
        """处理视频数据"""
        try:
            video_list = video_data.get('data', {}).get('data', {}).get('list', [])
            print(f"获取到 {len(video_list)} 个视频数据")
            return video_list
        except Exception as e:
            print(f"处理视频数据失败: {e}")
            return []