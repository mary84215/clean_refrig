"""手動推播快過期提醒：
python .\\scripts\\push_expire_soon.py --dry-run   只印出訊息，不推播
python .\\scripts\\push_expire_soon.py             立即推播一次
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 以絕對路徑把專案根目錄加入 sys.path，才能 import services / model / utlis
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.notify_food_service import NotifyFoodService  # noqa: E402
from utlis.logger import setup_logging  # noqa: E402


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="手動推播快過期提醒")
    parser.add_argument("--dry-run", action="store_true", help="只印出每位使用者會收到的訊息，不真的推播")
    args = parser.parse_args()

    setup_logging()
    count = asyncio.run(NotifyFoodService().push_expire_soon_notifications(dry_run=args.dry_run))
    print(f"{'預計' if args.dry_run else '成功'}推播 {count} 位使用者")
