"""專案設定：實際值放在專案根目錄的 .env（不進 git），這裡負責讀取與檢查"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _require(key: str) -> str:
    """讀取必填的環境變數，沒設定就丟出錯誤

    Args:
        key: 環境變數名稱

    Return:
        str: 環境變數的值
    """
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"環境變數 {key} 未設定，請在 .env 填入")
    return value


# MySQL 連線設定
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": _require("DB_USER"),
    "password": _require("DB_PASSWORD"),
    "database": _require("DB_NAME"),
}

# LINE Messaging API 設定（LINE Developers Console > Messaging API channel）
LINE_CHANNEL_ACCESS_TOKEN = _require("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = _require("LINE_CHANNEL_SECRET")

# 圖片辨識：預設用 Gemini；python run.py --fakellm 時改用假 API
USE_FAKE_LLM = os.getenv("USE_FAKE_LLM") == "1"

# 假 API
LLM_PARSE_URL = os.getenv("LLM_PARSE_URL", "http://localhost:8000/parse")

# Gemini（fake 模式不需要 API key）
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") if USE_FAKE_LLM else _require("GEMINI_API_KEY")
