"""啟動 API：python run.py（Gemini 辨識）或 python run.py --fakellm（假 API）"""
import argparse
import os

import uvicorn

HOST = "127.0.0.1"
PORT = 8001  # 8000 給假 LLM API 使用
RELOAD = True  # 開發用：改程式碼自動重啟


def parse_args() -> argparse.Namespace:
    """解析命令列參數

    Args:
        無

    Return:
        argparse.Namespace: fakellm 為 True 時改用假 API 辨識圖片
    """
    parser = argparse.ArgumentParser(description="啟動 clean_refrig API")
    parser.add_argument("--fakellm", action="store_true", help="圖片辨識改用假 API（localhost:8000/parse）")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    # reload 模式下 app 在子程序載入，用環境變數傳遞；明確設 0 避免殘留舊值
    os.environ["USE_FAKE_LLM"] = "1" if args.fakellm else "0"
    uvicorn.run("main:app", host=HOST, port=PORT, reload=RELOAD)
