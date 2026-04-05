"""
iceman-server — 抖音小冰人后端服务 (MVP Demo)

启动:
    cd iceman_server
    uvicorn app:app --host 0.0.0.0 --port 8080 --reload

或者直接:
    python app.py
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import config_router, conversations, me, summaries

app = FastAPI(
    title="抖音小冰人 API",
    description=(
        "IceMan backend service — demo MVP.\n\n"
        "身份: `X-User-Id` header 传 open_id，无 token 鉴权。\n"
        "演示主人: `owner_user_123`，演示访客: `visitor_user_456` 等。"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow all origins for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)
app.include_router(config_router.router)
app.include_router(conversations.router)
app.include_router(summaries.router)


@app.get("/health", tags=["internal"])
def health():
    return {"status": "ok", "service": "iceman-server", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
