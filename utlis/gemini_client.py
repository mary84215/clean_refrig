import json
from functools import lru_cache

from google import genai
from google.genai import errors, types
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from configs.configs import GEMINI_API_KEY, GEMINI_MODEL


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """取得全專案共用的 Gemini client，第一次呼叫時才建立（fake 模式不會建立）

    Args:
        無

    Return:
        genai.Client: Gemini client
    """
    return genai.Client(api_key=GEMINI_API_KEY)


def _is_retryable(exc: BaseException) -> bool:
    """判斷 Gemini 丟出的例外是否需要重試

    Args:
        exc: generate_json 執行時丟出的例外

    Return:
        bool: 5xx 或 429（額度/頻率限制）回傳 True；其餘回傳 False
    """
    if isinstance(exc, errors.ServerError):
        return True
    return isinstance(exc, errors.ClientError) and exc.code == 429


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True,
)
async def generate_json(
    image_bytes: bytes,
    content_type: str,
    system_prompt: str,
    schema: type[BaseModel],
) -> dict:
    """把圖片送給 Gemini，依指定 schema 回傳 JSON，失敗時最多重試 3 次

    Args:
        image_bytes: 圖片的原始 bytes
        content_type: 圖片的 MIME type，例如 "image/jpeg"
        system_prompt: 給模型的 system instruction
        schema: 要求模型回傳的 JSON 結構

    Return:
        dict: 模型回傳的 JSON
    """
    response = await get_gemini_client().aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=content_type)],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=schema,
            # 沒有用到 function calling，關掉避免每次呼叫都印出 AFC 警告
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    return json.loads(response.text)
