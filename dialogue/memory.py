from typing import Dict, Optional, List, Tuple
from config import ark_emb_client, ark_chat_client, STORAGE_PATH
import json
import os
import numpy as np
import time

class MemoryManager:
    def __init__(self):
        # 确保存储目录存在
        os.makedirs(STORAGE_PATH["embedding_cache"], exist_ok=True)
        # 内存存储
        self.memory_store = []
        # 加载现有内存
        self._load_memory()
    
    def _load_memory(self) -> None:
        """加载现有内存"""
        try:
            memory_dir = STORAGE_PATH["dialog_memory"]
            if os.path.exists(memory_dir):
                for filename in os.listdir(memory_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(memory_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                self.memory_store.append(data)
                        except Exception as e:
                            print(f"加载内存文件失败 {filepath}: {e}")
        except Exception as e:
            print(f"加载内存失败: {e}")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的embedding"""
        try:
            # 检查缓存
            cache_key = hash(text) % 1000000
            cache_file = os.path.join(STORAGE_PATH["embedding_cache"], f"emb_{cache_key}.json")
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # 调用API获取embedding
            response = ark_emb_client.embeddings.create(
                model="ep-20260213113345-kchpg",
                input=text
            )
            
            embedding = response.data[0].embedding
            
            # 缓存结果
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(embedding, f)
            
            return embedding
        except Exception as e:
            print(f"获取embedding失败: {e}")
            return None
    
    def similarity_search(self, query: str, top_k: int = 3) -> List[Dict]:
        """相似性搜索"""
        try:
            # 获取查询的embedding
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # 计算相似度
            results = []
            for memory in self.memory_store:
                # 获取对话摘要的embedding
                summary_embedding = self.get_embedding(memory.get("summary", ""))
                if summary_embedding:
                    # 计算余弦相似度
                    similarity = np.dot(query_embedding, summary_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(summary_embedding)
                    )
                    results.append({
                        "memory": memory,
                        "similarity": similarity
                    })
            
            # 按相似度排序，返回top_k
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return [result["memory"] for result in results[:top_k]]
        except Exception as e:
            print(f"相似性搜索失败: {e}")
            return []
    
    def add_memory(self, dialog_history: List[Dict], summary: str) -> None:
        """添加内存"""
        try:
            memory = {
                "timestamp": int(time.time()),
                "dialog_history": dialog_history,
                "summary": summary
            }
            self.memory_store.append(memory)
            # 保存到文件
            self._save_memory(memory)
        except Exception as e:
            print(f"添加内存失败: {e}")
    
    def filter_conversation(self, conversation_text: str) -> tuple[bool, str]:
        """过滤对话，判断是否需要显示给主人，返回 (should_show_to_host, reason)"""
        try:
            # 使用AI判断对话质量
            prompt = f"""
            请评估以下访客与小冰的对话内容，判断是否值得转达给主人：
            
            对话内容：
            {conversation_text}
            
            评估标准：
            1. 是否是高质量、有意义的对话
            2. 是否包含有价值的信息或见解
            3. 是否表现出真诚的兴趣而非套路式搭讪
            4. 是否尊重主人的边界
            
            输出格式：
            - 如果认为有价值："YES|理由说明"
            - 如果认为无价值："NO|理由说明"
            
            例如：
            - YES|这是一个关于艺术创作的深度讨论，访客展示了独特的见解
            - NO|这是典型的搭讪套话，缺乏实质内容
            """
            
            messages = [
                {"role": "system", "content": "你是一个社交对话质量评估专家，负责判断对话是否值得推荐给主人。"},
                {"role": "user", "content": prompt}
            ]
            
            response = ark_chat_client.chat.completions.create(
                model="ep-20260302134345-wxvcm",
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            
            if result.startswith("YES"):
                parts = result.split('|', 1)
                return True, parts[1] if len(parts) > 1 else "对话质量较高"
            else:
                parts = result.split('|', 1)
                return False, parts[1] if len(parts) > 1 else "对话质量较低"
        
        except Exception as e:
            print(f"过滤对话失败: {e}")
            return False, "评估失败，默认过滤"
    
    def store_filtered_conversation(self, conversation: Dict, should_show_to_host: bool) -> None:
        """存储过滤后的对话"""
        try:
            # 确保目录存在
            os.makedirs(STORAGE_PATH["dialog_memory"], exist_ok=True)
            
            # 生成文件名
            timestamp = int(time.time())
            filename = f"filtered_conversation_{timestamp}.json"
            filepath = os.path.join(STORAGE_PATH["dialog_memory"], filename)
            
            # 添加过滤标记
            conversation['should_show_to_host'] = should_show_to_host
            conversation['timestamp'] = timestamp
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, ensure_ascii=False, indent=2)
            
            print(f"对话已存储到: {filepath}, 显示给主人: {should_show_to_host}")
        except Exception as e:
            print(f"存储对话失败: {e}")
    
    def get_conversations_for_host(self) -> List[Dict]:
        """获取应该显示给主人的对话"""
        try:
            # 确保目录存在
            os.makedirs(STORAGE_PATH["dialog_memory"], exist_ok=True)
            
            conversations = []
            for filename in os.listdir(STORAGE_PATH["dialog_memory"]):
                if filename.startswith("filtered_conversation_") and filename.endswith(".json"):
                    filepath = os.path.join(STORAGE_PATH["dialog_memory"], filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        conversation = json.load(f)
                        if conversation.get('should_show_to_host', False):
                            conversations.append(conversation)
            
            # 按时间排序
            conversations.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            return conversations
        except FileNotFoundError:
            print(f"对话存储目录不存在: {STORAGE_PATH['dialog_memory']}")
            return []
        except Exception as e:
            print(f"获取对话失败: {e}")
            return []
    
    def _save_memory(self, memory: Dict) -> None:
        """保存内存到文件"""
        try:
            # 确保存储目录存在
            os.makedirs(STORAGE_PATH["dialog_memory"], exist_ok=True)
            
            # 生成文件名
            timestamp = memory.get("timestamp", int(time.time()))
            filename = f"dialog_{timestamp}.json"
            filepath = os.path.join(STORAGE_PATH["dialog_memory"], filename)
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存内存失败: {e}")
    
    def get_recent_memories(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """获取最近的内存"""
        try:
            cutoff_time = int(time.time()) - (days * 24 * 60 * 60)
            recent_memories = [
                memory for memory in self.memory_store
                if memory.get("timestamp", 0) >= cutoff_time
            ]
            # 按时间排序，返回最新的
            recent_memories.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return recent_memories[:limit]
        except Exception as e:
            print(f"获取最近内存失败: {e}")
            return []
    
    def clear_memory(self) -> None:
        """清空内存"""
        try:
            self.memory_store = []
            # 清空存储目录
            memory_dir = STORAGE_PATH["dialog_memory"]
            if os.path.exists(memory_dir):
                for filename in os.listdir(memory_dir):
                    filepath = os.path.join(memory_dir, filename)
                    os.remove(filepath)
            print("内存已清空")
        except Exception as e:
            print(f"清空内存失败: {e}")
    
    def mark_potential_connection(self, visitor_id: str, conversation_summary: str) -> None:
        """标记潜在连接对象"""
        try:
            # 确保目录存在
            os.makedirs(STORAGE_PATH["dialog_memory"], exist_ok=True)
            
            connection_data = {
                "visitor_id": visitor_id,
                "conversation_summary": conversation_summary,
                "timestamp": int(time.time()),
                "status": "potential_connection"  # 标记为潜在连接
            }
            
            # 生成文件名
            filename = f"connection_{visitor_id}_{int(time.time())}.json"
            filepath = os.path.join(STORAGE_PATH["dialog_memory"], filename)
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(connection_data, f, ensure_ascii=False, indent=2)
            
            print(f"访客 {visitor_id} 已标记为潜在连接对象")
        except Exception as e:
            print(f"标记潜在连接失败: {e}")
    
    def get_potential_connections(self) -> List[Dict]:
        """获取潜在连接对象列表"""
        try:
            # 确保目录存在
            os.makedirs(STORAGE_PATH["dialog_memory"], exist_ok=True)
            
            connections = []
            for filename in os.listdir(STORAGE_PATH["dialog_memory"]):
                if filename.startswith("connection_") and filename.endswith(".json"):
                    filepath = os.path.join(STORAGE_PATH["dialog_memory"], filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        connection = json.load(f)
                        connections.append(connection)
            
            # 按时间排序
            connections.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            return connections
        except FileNotFoundError:
            print(f"对话存储目录不存在: {STORAGE_PATH['dialog_memory']}")
            return []
        except Exception as e:
            print(f"获取潜在连接失败: {e}")
            return []