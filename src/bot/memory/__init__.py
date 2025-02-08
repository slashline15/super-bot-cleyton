# memory/__init__.py
import dotenv

dotenv.load_dotenv()

from .memory_manager import MemoryManager

__all__ = ['MemoryManager']
