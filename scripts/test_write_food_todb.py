import sys
from pathlib import Path

# 以絕對路徑把專案根目錄加入 sys.path，才能 import services / model / utlis
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.line_upload_food_service import LineUploadFoodService  # noqa: E402


if __name__ == '__main__':
    food_id = LineUploadFoodService().write_food_todb(
        user_id='test_user',
        category='fish',
        food_name='salmon',
        create_date='2025-01-01',
        valid_date='2026-12-12',
        days_left_to_notify=8
    )
    print(f"inserted id: {food_id}")
