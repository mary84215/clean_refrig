"""LINE 聊天機器人的食物登錄流程

流程 A（圖片）：
  使用者傳圖 → 辨識圖片中的食品資訊 → 回覆辨識結果 + 一行可複製的「登錄指令」

流程 B（文字）：
  使用者貼上「登錄 魚 鮭魚 2025-01-01 2026-02-02 3」→ 解析文字 → 寫入 DB → 回覆成功/失敗

不經過 LINE 的測試 API 見 route/test_api.py
"""
import re
from collections.abc import Awaitable, Callable
from datetime import date

import httpx
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from google.genai import errors as genai_errors
from pydantic import ValidationError

from configs.configs import GEMINI_MODEL, LLM_PARSE_URL, USE_FAKE_LLM
from model.food import FoodCreate, GeminiFoodSchema, ParseResult
from repository import upload_food_repository
from utlis.gemini_client import generate_json
from utlis.http_client import request_json
from utlis.image_utils import encode_image_to_base64
from utlis.logger import get_logger

logger = get_logger(__name__)


class FoodParseError(Exception):
    """圖片辨識失敗（LLM API 錯誤或回傳內容無法解析）"""


if USE_FAKE_LLM:
    logger.info("圖片辨識模式：假 API（%s）", LLM_PARSE_URL)
else:
    logger.info("圖片辨識模式：Gemini（%s）", GEMINI_MODEL)


class LineUploadFoodService:
    """LINE 聊天機器人的食物登錄流程：圖片辨識回覆、文字登錄指令；只回傳文字，不依賴 LINE SDK"""

    USAGE_TEXT = (
        "📷 傳一張食品照片給我，我會幫你辨識。或是自行登錄\n"
        "\n"
        "✍️ 登錄格式：\n登錄 <分類> <品名> <製造日> <有效日期> <提醒天數>\n"
        "\n"
        "例如：登錄 調味料 烤肉醬 2025-01-01 2026-02-02 3\n"
        "\n"
        "（*提醒天數＝到期前幾天提醒你）"
    )

    # 辨識結果預填的提醒天數，使用者可自行修改
    _DEFAULT_DAYS_LEFT_TO_NOTIFY = 3

    # 辨識不到的欄位在登錄指令裡的佔位字；使用者沒改就送出時，reply_for_text 會提示要改掉
    _PLACEHOLDERS = {
        "category": "<分類>",
        "food_name": "<品名>",
        "create_date": "<製造日>",
        "valid_date": "<有效日期>",
    }

    # 日期：實際日期，或該欄位的佔位字（讓 reply_for_text 能給出明確提示，而不是回用法說明）
    _DATE = r"\d{4}-\d{2}-\d{2}"
    _CREATE_DATE = rf"(?:{_DATE}|{re.escape(_PLACEHOLDERS['create_date'])})"
    _VALID_DATE = rf"(?:{_DATE}|{re.escape(_PLACEHOLDERS['valid_date'])})"

    # 登錄指令格式：登錄 <分類> <品名> <製造日> <有效期限> <到期前幾天提醒>
    _REGISTER_PATTERN = re.compile(
        rf"^登錄\s+(?P<category>\S+)\s+(?P<food_name>\S+)\s+(?P<create_date>{_CREATE_DATE})"
        rf"\s+(?P<valid_date>{_VALID_DATE})\s+(?P<days_left_to_notify>\d+)$"
    )

    _SYSTEM_PROMPT = """你現在是一個圖片文字辨識專家。幫我辨識圖片文字，並且判定與擷取以下資訊。辨識不到直接回傳空值。

欄位說明：
- category: 分類，例如「魚」
- food_name: 品名，例如「鮭魚」
- create_date: 製造日
- valid_date: 有效期限

規則：
- 日期一律轉成 YYYY-MM-DD 格式
- 辨識不到的欄位回傳 null，不要猜測

回傳範例：
{"category": "魚", "food_name": "鮭魚", "create_date": "2025-01-01", "valid_date": "2026-02-02"}"""

    def __init__(
        self,
        use_fake_llm: bool = USE_FAKE_LLM,
        fake_api_request: Callable[..., Awaitable[dict]] = request_json,
        gemini_generate: Callable[..., Awaitable[dict]] = generate_json,
        insert_food: Callable[[FoodCreate], int] = upload_food_repository.insert_food,
    ):
        """建立 service；依賴由外部傳入，測試時可換成假的 LLM 呼叫或寫 DB 函式

        Args:
            use_fake_llm: True 時用假 API 辨識，預設依 python run.py --fakellm 設定
            fake_api_request: 呼叫假 API 的函式，預設用 utlis.http_client 的 request_json
            gemini_generate: 呼叫 Gemini 的函式，預設用 utlis.gemini_client 的 generate_json
            insert_food: 寫入 DB 的函式，預設用 upload_food_repository 的 insert_food

        Return:
            None
        """
        self._use_fake_llm = use_fake_llm
        self._fake_api_request = fake_api_request
        self._gemini_generate = gemini_generate
        self._insert_food = insert_food

    async def reply_for_image(self, image_bytes: bytes) -> list[str]:
        """流程 A：辨識圖片，產生辨識結果與可複製的登錄指令

        Args:
            image_bytes: 使用者傳來的圖片內容

        Return:
            list[str]: 要回覆的訊息；成功為「辨識結果」與「登錄指令」兩則，失敗為一則錯誤提示
        """
        try:
            result = ParseResult.model_validate(await self.parse_food_image_bytes(image_bytes, "image/jpeg"))
        except FoodParseError as e:
            logger.warning("圖片辨識失敗：%s", e)
            return ["辨識失敗，請換一張清楚一點的照片再試試 📷"]

        values = {
            "category": result.category,
            "food_name": result.food_name,
            "create_date": result.create_date.isoformat() if result.create_date else None,
            "valid_date": result.valid_date.isoformat() if result.valid_date else None,
        }
        if all(v is None for v in values.values()):
            return ["看不出食品資訊，請換一張清楚的照片 📷"]

        def shown(key: str) -> str:
            """辨識結果顯示用：辨識不到顯示（未辨識）"""
            return values[key] or "（未辨識）"

        def filled(key: str) -> str:
            """登錄指令用：辨識不到填入佔位字，讓使用者自己改"""
            return values[key] or self._PLACEHOLDERS[key]

        has_missing = any(v is None for v in values.values())

        # 回覆兩則訊息：第二則只有指令本身，使用者長按就能整則複製
        register_cmd = (
            f"登錄 {filled('category')} {filled('food_name')} {filled('create_date')} {filled('valid_date')} "
            f"{self._DEFAULT_DAYS_LEFT_TO_NOTIFY}"
        )
        hint = (
            "⚠️ 有欄位沒辨識到，請複製下一則訊息，把佔位字改成正確內容再傳給我 👇"
            if has_missing
            else "確認無誤請複製下一則訊息傳給我；有錯可以直接修改後再傳 👇"
        )
        return [
            (
                "🔍 辨識結果\n"
                f"分類：{shown('category')}\n"
                f"品名：{shown('food_name')}\n"
                f"製造日：{shown('create_date')}\n"
                f"有效期限：{shown('valid_date')}\n\n"
                f"最後的數字是「到期前幾天提醒你」，預設 {self._DEFAULT_DAYS_LEFT_TO_NOTIFY} 天。\n"
                "\n"
                f"{hint}"
            ),
            register_cmd,
        ]

    async def reply_for_text(self, user_id: str, text: str) -> list[str]:
        """流程 B：解析使用者傳來的登錄指令並寫入 DB；格式不符則回覆用法說明

        Args:
            user_id: LINE 使用者 id
            text: 使用者傳來的文字

        Return:
            list[str]: 要回覆的訊息（登錄成功、資料有誤或用法說明）
        """
        match = self._REGISTER_PATTERN.match(text.strip())
        if not match:
            return [self.USAGE_TEXT]

        fields = match.groupdict()
        problems = [
            f"請將{placeholder}取代為實際內容"
            for key, placeholder in self._PLACEHOLDERS.items()
            if fields[key] == placeholder
        ]
        if problems:
            return ["⚠️ 還有欄位沒填\n" + "\n".join(problems)]

        try:
            # pymysql 是同步的，丟到 threadpool 避免卡住 event loop
            await run_in_threadpool(self.write_food_todb, user_id=user_id, **fields)
        except (ValueError, ValidationError):
            # ValidationError 繼承自 ValueError；日期不存在或有效期限早於製造日都會到這
            return [f"⚠️ 資料有誤，請檢查日期是否正確\n\n{self.USAGE_TEXT}"]

        return [
            f"✅ 已登錄！\n{fields['food_name']}（{fields['category']}，有效期限 {fields['valid_date']}，"
            f"到期前 {fields['days_left_to_notify']} 天提醒）"
        ]

    async def parse_food_image_bytes(self, image_bytes: bytes, content_type: str) -> dict:
        """辨識圖片中的食品資訊；非圖片類型丟出 ValueError，辨識失敗丟出 FoodParseError

        Args:
            image_bytes: 圖片的原始 bytes
            content_type: 圖片的 MIME type，例如 "image/jpeg"

        Return:
            dict: {"category", "food_name", "create_date", "valid_date"}，辨識不到的欄位為 None
        """
        if not content_type or not content_type.startswith("image/"):
            raise ValueError(f"Unsupported file type: {content_type}")

        try:
            if self._use_fake_llm:
                raw = await self._parse_with_fake_api(image_bytes, content_type)
            else:
                raw = await self._parse_with_gemini(image_bytes, content_type)
        except (httpx.HTTPError, genai_errors.APIError) as e:
            raise FoodParseError(f"LLM API error: {e}") from e
        except (ValueError, TypeError) as e:
            # 回傳不是合法 JSON（或被安全機制擋下沒有內容）
            raise FoodParseError(f"LLM response is not valid JSON: {e}") from e

        if not isinstance(raw, dict):
            raise FoodParseError(f"LLM response is not a JSON object: {raw!r}")
        return ParseResult.model_validate(raw).model_dump(mode="json")

    async def parse_food_image(self, file: UploadFile) -> dict:
        """讀取上傳的圖片檔並辨識食品資訊（給 route/test_api.py 使用）

        Args:
            file: 使用者上傳的圖片檔

        Return:
            dict: {"category", "food_name", "create_date", "valid_date"}，辨識不到的欄位為 None
        """
        image_bytes = await file.read()
        return await self.parse_food_image_bytes(image_bytes, file.content_type)

    def write_food_todb(self, user_id: str, category: str, food_name: str, create_date: date, valid_date: date, days_left_to_notify: int) -> int:
        """驗證食物資料後寫入 DB；有效期限早於製造日會丟出 ValueError

        Args:
            user_id: LINE 使用者 id
            category: 分類，例如「魚」
            food_name: 品名，例如「鮭魚」
            create_date: 製造日
            valid_date: 有效期限
            days_left_to_notify: 到期前幾天提醒

        Return:
            int: 新增資料的 id
        """
        food = FoodCreate(user_id=user_id, category=category, food_name=food_name, create_date=create_date, valid_date=valid_date, days_left_to_notify = days_left_to_notify)
        if food.valid_date < food.create_date:
            raise ValueError("valid_date must not be earlier than create_date")
        return self._insert_food(food)

    async def _parse_with_fake_api(self, image_bytes: bytes, content_type: str) -> dict:
        """呼叫假 API 辨識圖片（python run.py --fakellm 時使用）

        Args:
            image_bytes: 圖片的原始 bytes
            content_type: 圖片的 MIME type

        Return:
            dict: 假 API 回傳的固定結果
        """
        payload = {"image_base64": encode_image_to_base64(image_bytes), "content_type": content_type}
        return await self._fake_api_request("GET", LLM_PARSE_URL, json=payload)

    async def _parse_with_gemini(self, image_bytes: bytes, content_type: str) -> dict:
        """呼叫 Gemini 辨識圖片文字並擷取食品資訊

        Args:
            image_bytes: 圖片的原始 bytes
            content_type: 圖片的 MIME type

        Return:
            dict: Gemini 回傳的 JSON
        """
        return await self._gemini_generate(image_bytes, content_type, self._SYSTEM_PROMPT, GeminiFoodSchema)
