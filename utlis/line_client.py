from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    PushMessageRequest,
    TextMessage,
)

from configs.configs import LINE_CHANNEL_ACCESS_TOKEN
from utlis.logger import get_logger

logger = get_logger(__name__)

# 全專案共用的 LINE Messaging API 設定
line_configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)


class LinePushClient:
    """LINE push message 的共用封裝"""

    def __init__(self, configuration: Configuration = line_configuration):
        """建立推播 client

        Args:
            configuration: LINE Messaging API 設定，預設用全專案共用的 line_configuration

        Return:
            None
        """
        self._configuration = configuration

    async def push_texts(self, messages: dict[str, str]) -> int:
        """推播文字訊息給多位使用者；單一使用者失敗只記 log，不影響其他人

        Args:
            messages: {user_id: 要推播的文字}

        Return:
            int: 成功推播的人數
        """
        sent = 0
        async with AsyncApiClient(self._configuration) as api_client:
            line_api = AsyncMessagingApi(api_client)
            for user_id, text in messages.items():
                try:
                    await line_api.push_message(
                        PushMessageRequest(to=user_id, messages=[TextMessage(text=text)])
                    )
                    sent += 1
                except Exception:
                    logger.exception("LINE 推播失敗：user_id=%s", user_id)
        return sent
