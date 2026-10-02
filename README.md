# clean_refrig 冰箱食物管理 LINE 機器人

用 LINE 聊天機器人登錄冰箱裡的食物，快過期時每天自動提醒。

## 功能

- **拍照辨識**：在 LINE 傳一張食品包裝照片，機器人用 Gemini 辨識分類、品名、製造日、有效期限，回覆一則可直接複製的登錄指令。
- **文字登錄**：把登錄指令傳回給機器人（或自己手打），資料寫進 MySQL。每個欄位一行，品名可以含空白：
  ```
  登錄
  <分類>
  <品名>
  <製造日>
  <有效日期>
  <提醒天數>
  ```
  例如：
  ```
  登錄
  飲料
  御茶園 日式麥茶
  2025-01-01
  2027-06-24
  3
  ```
  辨識不到的欄位會以 `<分類>`、`<有效日期>` 等佔位字預填，沒改就送出時機器人會提示要改哪一欄。製造日不知道可以保留 `<製造日>`，DB 會存 NULL。
- **快過期提醒**：每天台灣時間 17:00 查出「有效期限 − 今天 ≤ 提醒天數」的食物（含已過期），依使用者分組用 LINE 推播。

## 環境需求

- Windows + Miniconda（`C:\ProgramData\miniconda3`）
- MySQL
- LINE Messaging API channel（LINE Developers Console）
- Gemini API key
- 本機開發接 LINE webhook 需要 ngrok（LINE 只接受公開 HTTPS 網址）

## 安裝

1. 建立 conda 環境 `clean_frig`（Python 3.14）並安裝 `requirements.txt`：
   ```
   setup_env.bat
   ```
2. 在專案根目錄建立 `.env`（不進 git），填入以下變數：

   | 變數 | 必填 | 說明 |
   |---|---|---|
   | `DB_HOST` | | 預設 `localhost` |
   | `DB_PORT` | | 預設 `3306` |
   | `DB_USER` | ✓ | MySQL 帳號 |
   | `DB_PASSWORD` | ✓ | MySQL 密碼 |
   | `DB_NAME` | ✓ | 資料庫名稱，例如 `clean_refrig` |
   | `LINE_CHANNEL_ACCESS_TOKEN` | ✓ | LINE channel access token |
   | `LINE_CHANNEL_SECRET` | ✓ | LINE channel secret |
   | `GEMINI_API_KEY` | ✓（`--fakellm` 時可省略） | Gemini API key |
   | `GEMINI_MODEL` | | 預設 `gemini-3.5-flash-lite` |
   | `LLM_PARSE_URL` | | 假 API 位址，預設 `http://localhost:8000/parse` |

   必填值沒設定時，程式一啟動就會報錯並指出缺哪一個。
3. 建立資料庫與資料表（依 `sql/schema.sql`，可重複執行）：
   ```
   conda activate clean_frig
   python -m utlis.init_db
   ```

## 執行

```
conda activate clean_frig
python run.py              # 用 Gemini 辨識圖片
python run.py --fakellm    # 改用假 API（localhost:8000/parse），不耗 Gemini 額度
```

- API 跑在 `http://127.0.0.1:8001`，開發模式下改程式碼會自動重啟（改 `.env` 需手動重啟）。
- 快過期推播排程跟著 API 一起啟動，API 開著才會推播。
- 接上 LINE：`ngrok http 8001`，在 LINE Developers Console 把 Webhook URL 設為 `https://<ngrok 網址>/callback` 並開啟 Use webhook。

### API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/callback` | LINE webhook（會驗證簽章） |
| POST | `/food/parse` | 測試用：上傳圖片，回傳辨識結果 JSON |
| POST | `/food` | 測試用：直接寫入一筆食物資料 |

啟動後可在 `http://127.0.0.1:8001/docs` 直接測試。

### 手動工具

```
python .\scripts\push_expire_soon.py --dry-run   # 預覽每位使用者會收到的快過期提醒，不推播
python .\scripts\push_expire_soon.py             # 立即推播一次
python .\scripts\test_write_food_todb.py         # 寫入一筆測試資料
```

Log 寫在 `logs/log_yyyy-mm-dd.log`（每天一個檔，不進 git）。

## 專案結構

```
route/        接收 HTTP / LINE 事件、呼叫 service、回應
  line_webhook_route.py     LINE webhook
  test_api.py               測試用 API（/food/parse、/food）
services/     業務邏輯
  line_upload_food_service.py   圖片辨識、登錄指令、寫入 DB
  notify_food_service.py        快過期提醒（查詢、組訊息、推播）
repository/   DB 存取（SQL）
jobs/         排程設定（每天 17:00 推播）
model/        資料結構（pydantic model）
utlis/        共用工具：logger、HTTP / Gemini / LINE client、建表
configs/      設定（從 .env 讀取）
sql/          資料表定義
scripts/      手動執行的工具
```

開發規範見 [CLAUDE.md](CLAUDE.md)。

## 待開發
1. 使用者刪除品項(用queue) VVV
2. 使用者查詢品項(by cache) VVV
3. 排成發送多下DELETE=0
4. 部署用k8s
5. Airflow調度排程
6. (V) 製造日允許空 VVV
7. 輸入格式改用換行 VVV
8. 辨識也改用queue, 因為LLM解析要時間會塞車
