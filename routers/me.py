from fastapi import APIRouter, Header

from core.response import err, ok
from services.data_service import get_user

router = APIRouter()


@router.get("/iceman/v1/me")
def get_me(x_user_id: str = Header(...)):
    """Return current user's profile (from user_data.json)."""
    user = get_user(x_user_id)
    if not user:
        return err(40101, "用户不存在")
    return ok({
        "open_id":   user["open_id"],
        "nickName":  user.get("nickName", ""),
        "avatarUrl": user.get("avatarUrl", ""),
        "gender":    user.get("gender", 0),
        "city":      user.get("city", ""),
        "province":  user.get("province", ""),
        "country":   user.get("country", "中国"),
        "role":      user.get("role", "visitor"),
    })
