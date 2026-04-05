from typing import Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel

from core.response import err, ok
from services.data_service import (
    get_iceman_config,
    get_persona_templates,
    get_user,
    get_videos_for_frontend,
    save_iceman_config,
)

router = APIRouter()


# ── IceMan config ────────────────────────────────────────────────────────────

@router.get("/iceman/v1/config")
def get_config(x_user_id: str = Header(...)):
    """Return current IceMan configuration."""
    cfg = get_iceman_config()
    templates = get_persona_templates()
    persona_name = next(
        (t["name"] for t in templates if t["template_id"] == cfg.get("persona_template_id")),
        "",
    )
    return ok({
        "iceman_id":          cfg["iceman_id"],
        "nickname":           cfg["nickname"],
        "status":             cfg["status"],
        "persona_template_id": cfg["persona_template_id"],
        "persona_name":       persona_name,
    })


class ConfigUpdateBody(BaseModel):
    action: str                          # enable | disable | update
    nickname: Optional[str] = None
    persona_template_id: Optional[str] = None


@router.put("/iceman/v1/config")
def update_config(body: ConfigUpdateBody, x_user_id: str = Header(...)):
    """Update IceMan config (enable/disable/rename/switch persona)."""
    cfg = get_iceman_config()
    if body.action == "enable":
        cfg["status"] = "enabled"
    elif body.action == "disable":
        cfg["status"] = "disabled"
    if body.nickname is not None:
        cfg["nickname"] = body.nickname
    if body.persona_template_id is not None:
        cfg["persona_template_id"] = body.persona_template_id
    save_iceman_config(cfg)
    return ok(cfg)


# ── Persona templates ────────────────────────────────────────────────────────

@router.get("/iceman/v1/persona-templates")
def list_templates(x_user_id: str = Header(...)):
    """Return all available persona templates."""
    templates = get_persona_templates()
    return ok({"templates": templates})


# ── Videos (owner's published videos) ────────────────────────────────────────

@router.get("/iceman/v1/videos")
def list_videos(x_user_id: str = Header(...)):
    """Return the owner's mock video list (for frontend display)."""
    videos = get_videos_for_frontend()
    return ok({"item_list": videos, "total": len(videos)})
