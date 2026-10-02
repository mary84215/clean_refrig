"""LINE webhook：驗證簽章、依訊息類型分派給 LineUploadFoodService，並把回傳的文字回覆給使用者

業務流程（圖片辨識、登錄指令）在 services/line_upload_food_service.py
"""
from fastapi import APIRouter, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    AsyncMessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import ImageMessageContent, MessageEvent, TextMessageContent

from configs.configs import LINE_CHANNEL_SECRET
from services.line_upload_food_service import LineUploadFoodService
from utlis.line_client import line_configuration
from utlis.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["line"])

parser = WebhookParser(LINE_CHANNEL_SECRET)
line_upload_food_service = LineUploadFoodService()


@router.post("/callback")
async def callback(request: Request):
    """LINE webhook 入口：驗證簽章後，依訊息類型交給 LineUploadFoodService 處理並回覆使用者

    Args:
        request: LINE 平台送來的 webhook 請求

    Return:
        str: "OK"，告知 LINE 已收到；簽章錯誤則回 400
    """
    signature = request.headers.get("X-Line-Signature", "")
    body = (await request.body()).decode("utf-8")  # 驗簽必須用原始 body

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    async with AsyncApiClient(line_configuration) as api_client:
        line_api = AsyncMessagingApi(api_client)
        blob_api = AsyncMessagingApiBlob(api_client)

        for event in events:
            if not isinstance(event, MessageEvent):
                continue
            try:
                if isinstance(event.message, ImageMessageContent):
                    # LINE 只給 message id，要再下載圖片本體
                    image_bytes = await blob_api.get_message_content(event.message.id)
                    texts = await line_upload_food_service.reply_for_image(image_bytes)
                elif isinstance(event.message, TextMessageContent):
                    texts = await line_upload_food_service.reply_for_text(event.source.user_id, event.message.text)
                else:
                    texts = [LineUploadFoodService.USAGE_TEXT]
            except Exception:
                logger.exception("處理事件失敗")
                texts = ["系統忙碌中，請稍後再試 🙏"]

            await line_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=text) for text in texts],
                )
            )

    return "OK"
