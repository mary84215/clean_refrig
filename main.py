from contextlib import asynccontextmanager

from fastapi import FastAPI

from utlis.logger import setup_logging

# 要在 import 其他模組前設定，它們 import 時印的 log（例如辨識模式）才會寫進檔案
setup_logging()

from jobs.job import shutdown_scheduler, start_scheduler  # noqa: E402
from route.line_webhook_route import router as line_webhook_router  # noqa: E402
from route.test_api import router as test_api_router  # noqa: E402
from utlis.http_client import close_http_client  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理 app 的啟動與關閉；啟動時開始每日推播排程，關閉時停止排程並釋放共用的 http client

    Args:
        app: FastAPI app

    Return:
        AsyncIterator[None]: 供 FastAPI 使用的 lifespan context
    """
    start_scheduler()
    yield
    shutdown_scheduler()
    await close_http_client()


app = FastAPI(lifespan=lifespan)
app.include_router(test_api_router)
app.include_router(line_webhook_router)

