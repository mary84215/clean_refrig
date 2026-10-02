"""測試用 API：不經過 LINE，直接測試圖片辨識與寫入 DB"""
from fastapi import APIRouter, File, HTTPException, UploadFile

from model.food import FoodCreate
from services.line_upload_food_service import FoodParseError, LineUploadFoodService

router = APIRouter(prefix="/food", tags=["test"])
line_upload_food_service = LineUploadFoodService()


@router.post("/parse")
async def parse_food(file: UploadFile = File(...)) -> dict:
    """API：上傳食物圖片，交給 LLM 辨識；非圖片回 400，辨識失敗回 502

    Args:
        file: 使用者上傳的圖片（multipart/form-data）

    Return:
        dict: {"category", "food_name", "create_date", "valid_date"}，辨識不到的欄位為 null
    """
    try:
        return await line_upload_food_service.parse_food_image(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FoodParseError as e:
        raise HTTPException(status_code=502, detail=str(e))


# pymysql 是同步阻塞的，用一般 def 讓 FastAPI 丟到 threadpool 執行
@router.post("", status_code=201)
def create_food(food: FoodCreate) -> dict:
    """API：將食物資料寫入 DB；資料不合理（例如有效期限早於製造日）回 400

    Args:
        food: request body 的食物資料

    Return:
        dict: {"id": 新增資料的 id}
    """
    try:
        food_id = line_upload_food_service.write_food_todb(**food.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": food_id}
