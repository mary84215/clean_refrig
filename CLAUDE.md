# clean_refrig 開發法則

你是這個專案的軟體工程師。開發時遵守以下規則；規則有衝突或不清楚時先問，不要自行假設。

## 1. 分層
| 層 | 位置 | 只做什麼 | 不做什麼 |
|---|---|---|---|
| route | `route/` | 接收 HTTP / LINE 事件、呼叫 service、把結果或錯誤轉成回應 | 不寫業務邏輯、不直接查 DB |
| services | `services/` | 業務邏輯（例如：哪些食物快過期、訊息怎麼寫、推播給誰） | 不寫 SQL、不含排程設定 |
| repository | `repository/` | 撈 / 寫 DB 的指令（SQL） | 不含業務判斷 |
| jobs | `jobs/` | 排程設定（幾點執行、呼叫哪個 service） | 不含業務邏輯 |
| model | `model/` | 資料結構（pydantic model） | |

## 2. Logging
- 統一從 `utlis/logger.py` 取得 logger：`from utlis.logger import get_logger`、`logger = get_logger(__name__)`，不要直接 `import logging` 建 logger。格式與輸出由 `setup_logging()` 決定（寫入 `logs/log_yyyy-mm-dd.log`）。
- 不要自己新增 handler、formatter 或 `print` 當 log。

## 3. 重用既有程式
新增前先找有沒有現成的 function / method，有就引用，不要重寫一份。常用的：
- HTTP 請求：`utlis/http_client.py` 的 `request_json`（已含重試）
- Gemini：`utlis/gemini_client.py` 的 `generate_json`
- 圖片 base64：`utlis/image_utils.py` 的 `encode_image_to_base64`
- LINE 推播：`utlis/line_client.py` 的 `LinePushClient`（設定共用 `line_configuration`）
- 設定值：`configs/configs.py`

## 4. 降低耦合
- 下層不 import 上層：repository 不 import services；services 不 import route / jobs。
- 函式透過參數取得需要的東西，不依賴其他模組的內部變數。
- class 內只給自己用的 method / 常數以 `_` 開頭，只公開外部真的會呼叫的。

## 5. Docstring
所有 function / method 都要有，格式統一：
```python
"""說明做什麼（需要時可以多行，例如補充例外或注意事項）

Args:
    參數名: 說明（沒有參數寫「無」）

Return:
    型別: 說明
"""
```

## 6. 共用元件
跨層共用的工具放 `utlis/`（注意資料夾名稱是 utlis）。

## 7. 機密資訊
- token、密碼、API key 只放 `.env`（不進 git），程式一律透過 `configs/configs.py` 讀取，不在其他地方直接 `os.getenv`。
- 不要讀取或印出 `.env` 的內容；需要新的變數名稱時直接問。

## 補充（目前專案已在用的慣例）
- pymysql 是同步的：在 async 函式裡查 DB 要用 `run_in_threadpool`。
- 執行：`conda activate clean_frig` 後 `python run.py`（`--fakellm` 改用假 API）；手動測試 script 放 `scripts/`。
- 新套件加到 `requirements.txt`。
