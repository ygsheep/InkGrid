"""FastAPI 应用入口：app 实例 + 中间件 + 异常处理器 + 路由注册。

启动：uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import admin, public, ws
from app.config import get_settings
from app.core.errors import AppError, to_envelope
from app.core.logging import configure_logging, get_logger, new_request_id
from app.db.redis import close_redis
from app.db.session import engine

settings = get_settings()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期。"""
    configure_logging(debug=settings.debug)
    logger.info("startup", app=settings.app_name, debug=settings.debug)
    yield
    logger.info("shutdown")
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.site_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)


# ===== 中间件 =====


class RequestIdMiddleware(BaseHTTPMiddleware):
    """为每请求注入 request_id，写入上下文与响应头 X-Request-Id。"""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or new_request_id()
        # 上下文已由 new_request_id 设置
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response


app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    # localhost 与 127.0.0.1 浏览器视为不同 origin，需同时允许；
    # settings.next_public_api_base 由 .env 控制（生产部署时设为实际域名）。
    allow_origins=[
        settings.next_public_api_base,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)


# ===== 异常处理器 =====


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """业务异常 → envelope。"""
    return JSONResponse(
        status_code=exc.status_code,
        content=to_envelope(exc),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic 校验失败 → envelope {code, data:{errors}, message}。

    FastAPI 的 errors() 里 input 可能是 bytes（原始请求体），
    标准 json.dumps 不能序列化 bytes，需要清洗。
    """
    def _safe(v):
        if isinstance(v, (bytes, bytearray)):
            try:
                return v.decode("utf-8")
            except Exception:
                return f"<bytes len={len(v)}>"
        return v

    errors = []
    for e in exc.errors():
        clean = {}
        for k, v in e.items():
            if isinstance(v, (list, tuple)):
                clean[k] = [_safe(x) for x in v]
            else:
                clean[k] = _safe(v)
        errors.append(clean)

    return JSONResponse(
        status_code=422,
        content={
            "code": 4220,
            "data": {"errors": errors},
            "message": "参数校验失败",
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """兜底：未捕获异常 → envelope，避免泄露堆栈。"""
    logger.exception("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"code": 5000, "data": None, "message": "服务器内部错误"},
    )


# ===== 路由 =====
app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin")
app.include_router(ws.router)  # WS 路由自行处理前缀


@app.get("/health")
async def health() -> dict:
    """健康检查。"""
    return {"code": 0, "data": {"status": "ok"}, "message": "ok"}
