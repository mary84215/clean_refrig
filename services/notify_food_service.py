from collections import defaultdict
from collections.abc import Callable
from datetime import date

from fastapi.concurrency import run_in_threadpool

from model.food import ExpireSoonFood
from repository.query_expire_soon_food_repository import query_expire_soon_food
from utlis.line_client import LinePushClient
from utlis.logger import get_logger

logger = get_logger(__name__)


class NotifyFoodService:
    """快過期提醒的業務邏輯：查快過期食物、組訊息、推播給使用者
    若使用者底下有快過期食物，那會觸發提醒(過期定義由使者將食物寫入DB時候定義)
    """

    # 單則訊息最多列幾項（LINE 單則文字上限 5000 字）
    MAX_ITEMS_PER_MESSAGE = 30

    def __init__(
        self,
        query_foods: Callable[[], list[ExpireSoonFood]] = query_expire_soon_food,
        line_client: LinePushClient | None = None,
    ):
        """建立 service；依賴由外部傳入，測試時可換成假的查詢函式或假的推播 client

        Args:
            query_foods: 查詢所有使用者快過期食物的函式，預設查 DB
            line_client: 推播用的 LINE client，None 時用預設的 LinePushClient

        Return:
            None
        """
        self._query_foods = query_foods
        self._line_client = line_client or LinePushClient()

    @staticmethod
    def _describe_days_left(valid_date: date, today: date) -> str:
        """依有效期限與今天的差距，產生「已過期 / 今天到期 / 剩 N 天」的說明

        Args:
            valid_date: 有效期限
            today: 今天日期

        Return:
            str: 例如「已過期 2 天（2026-09-26）」、「今天到期」、「剩 3 天（2026-10-01）」
        """
        days_left = (valid_date - today).days
        if days_left < 0:
            return f"已過期 {-days_left} 天（{valid_date}）"
        if days_left == 0:
            return "今天到期"
        return f"剩 {days_left} 天（{valid_date}）"

    @staticmethod
    def build_expire_soon_message(items: list[ExpireSoonFood], today: date) -> str:
        """組一位使用者的快過期提醒訊息

        Args:
            items: 該使用者快過期（含已過期）的食物，已依有效期限排序
            today: 今天日期

        Return:
            str: 要推播的文字訊息
        """
        limit = NotifyFoodService.MAX_ITEMS_PER_MESSAGE
        lines = [f"⏰ 快過期提醒（共 {len(items)} 項）"]
        for item in items[:limit]:
            lines.append(
                f"• {item.food_name}（{item.category}）"
                f"{NotifyFoodService._describe_days_left(item.valid_date, today)}"
            )
        if len(items) > limit:
            lines.append(f"…還有 {len(items) - limit} 項")
        return "\n".join(lines)

    def get_expire_soon_messages(self, today: date) -> dict[str, str]:
        """查出所有使用者快過期（含已過期）的食物，依使用者分組並組好提醒訊息

        Args:
            today: 今天日期

        Return:
            dict[str, str]: {user_id: 要給該使用者的提醒訊息}；沒有快過期食物的使用者不會出現
        """
        foods_by_user: dict[str, list[ExpireSoonFood]] = defaultdict(list)
        for food in self._query_foods():
            foods_by_user[food.user_id].append(food)
        return {user_id: self.build_expire_soon_message(items, today) for user_id, items in foods_by_user.items()}

    async def push_expire_soon_notifications(self, dry_run: bool = False) -> int:
        """推播快過期提醒給每位有快過期食物的使用者；單一使用者失敗不影響其他人

        Args:
            dry_run: True 時只記 log 顯示訊息內容，不真的推播

        Return:
            int: 成功推播（dry_run 時為預計推播）的使用者人數
        """
        # 查 DB 用的 pymysql 是同步的，丟到 threadpool 避免卡住 event loop
        messages = await run_in_threadpool(self.get_expire_soon_messages, date.today())

        if dry_run:
            for user_id, text in messages.items():
                logger.info("[dry-run] 推播給 %s：\n%s", user_id, text)
            return len(messages)

        sent = await self._line_client.push_texts(messages)
        logger.info("快過期提醒推播完成：成功 %d / 共 %d 位使用者", sent, len(messages))
        return sent
