import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# 全專案共用的 client（連線池可重複使用）
http_client = httpx.AsyncClient(timeout=30)


def _is_retryable(exc: BaseException) -> bool:
    """判斷 request_json 丟出的例外是否需要重試

    Args:
        exc: request_json 執行時丟出的例外

    Return:
        bool: 網路錯誤、逾時或 5xx 回傳 True；其餘（含 4xx）回傳 False
    """
    # 網路錯誤 / 逾時，或 5xx 才重試；4xx 是呼叫端錯誤，不重試
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True,
)
async def request_json(method: str, url: str, **kwargs) -> dict:
    """用共用 client 發送 HTTP 請求並回傳 JSON，失敗時最多重試 3 次

    Args:
        method: HTTP method，例如 "GET"、"POST"
        url: 請求的網址
        **kwargs: 其他傳給 httpx 的參數，例如 json、params、headers

    Return:
        dict: 回應 body 解析後的 JSON
    """
    resp = await http_client.request(method, url, **kwargs)
    resp.raise_for_status()
    return resp.json()


async def close_http_client() -> None:
    """關閉共用的 http client，釋放連線池，於 app 關閉時呼叫

    Args:
        無

    Return:
        None
    """
    await http_client.aclose()
