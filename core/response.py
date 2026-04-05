"""Standard API response helpers."""
from typing import Any


def ok(data: Any = None) -> dict:
    return {"code": 0, "message": "success", "data": data}


def err(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None}
