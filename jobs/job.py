"""排程工作：只負責「什麼時候做」，實際推播邏輯在 services.notify_food_service"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.notify_food_service import NotifyFoodService
from utlis.logger import get_logger

logger = get_logger(__name__)

TIMEZONE = "Asia/Taipei"

scheduler = AsyncIOScheduler(timezone=TIMEZONE)
notify_food_service = NotifyFoodService()


def start_scheduler() -> None:
    """啟動排程：每天下午 5:00（台灣時間）推播快過期提醒

    Args:
        無

    Return:
        None
    """
    job = scheduler.add_job(
        notify_food_service.push_expire_soon_notifications,
        CronTrigger(hour=17, minute=0, timezone=TIMEZONE),
        id="push_expire_soon",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("快過期提醒排程已啟動，下次執行：%s", job.next_run_time)


def shutdown_scheduler() -> None:
    """停止排程，於 app 關閉時呼叫

    Args:
        無

    Return:
        None
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
