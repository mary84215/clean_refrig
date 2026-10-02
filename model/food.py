from datetime import date

from pydantic import BaseModel, field_validator


class FoodCreate(BaseModel):
    user_id: str
    category: str
    food_name: str
    create_date: date | None  # 不知道製造日時為 None（DB 存 NULL）
    valid_date: date
    days_left_to_notify: int


class ExpireSoonFood(BaseModel):
    """快過期（含已過期）的食物，給 LINE 推播用"""

    user_id: str
    category: str
    food_name: str
    valid_date: date
    days_left_to_notify: int


class GeminiFoodSchema(BaseModel):
    """要求 Gemini 回傳的 JSON 結構；日期先用字串，之後由 ParseResult 轉換"""

    category: str | None
    food_name: str | None
    create_date: str | None
    valid_date: str | None


class ParseResult(BaseModel):
    """圖片辨識結果；辨識不到的欄位為 None"""

    category: str | None = None
    food_name: str | None = None
    create_date: date | None = None
    valid_date: date | None = None

    @field_validator("category", "food_name", mode="before")
    @classmethod
    def _blank_to_none(cls, value):
        """空字串視為辨識不到

        Args:
            value: 原始欄位值

        Return:
            去除前後空白後的字串；空字串或 None 回傳 None
        """
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("create_date", "valid_date", mode="before")
    @classmethod
    def _parse_date_or_none(cls, value):
        """日期不是 YYYY-MM-DD 就視為辨識不到，交給使用者手動補

        Args:
            value: 原始欄位值

        Return:
            date | None: 解析成功回傳 date，否則 None
        """
        if isinstance(value, date):
            return value
        if not value:
            return None
        try:
            return date.fromisoformat(str(value).strip())
        except ValueError:
            return None
