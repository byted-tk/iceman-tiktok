"""
dialogue package — LLM module for iceman-server.

Bootstrap: add this directory to sys.path so internal flat imports
(e.g. `from config import ...`) keep working without modification.
Then re-export the key classes so callers can do:

    from dialogue import UserDialogueManager, MemoryManager, ...

LLM 同学开发说明（@袁嘉豪）:
  - 在 dialogue/ 目录下继续用 flat import 风格开发，无需改动
  - 后端通过 `from dialogue import XxxManager` 调用，接口在此文件声明
  - 新增的类/函数请在本文件 __all__ 中注册，方便后端感知
"""
import sys
import os

# Add this directory to sys.path so internal files can `from config import ...`
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

# Re-export key classes as package-level names
from user_dialogue import UserDialogueManager      # noqa: E402
from host_dialogue import HostDialogueManager      # noqa: E402
from memory import MemoryManager                   # noqa: E402
from privacy_manager import PrivacyManager         # noqa: E402
from user_manager import UserManager               # noqa: E402
from vlm import VLMManager                         # noqa: E402

__all__ = [
    "UserDialogueManager",
    "HostDialogueManager",
    "MemoryManager",
    "PrivacyManager",
    "UserManager",
    "VLMManager",
]
