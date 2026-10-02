import pymysql

from model.food import FoodCreate
from configs.configs import DB_CONFIG


def insert_food(food: FoodCreate) -> int:
    """將一筆食物資料寫入 food 表

    Args:
        food: 要寫入的食物資料

    Return:
        int: 新增資料的 id
    """
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO food (user_id, category, food_name, create_date, valid_date, days_left_to_notify) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    food.user_id,
                    food.category,
                    food.food_name,
                    food.create_date,
                    food.valid_date,
                    food.days_left_to_notify,
                ),
            )
            food_id = cursor.lastrowid
        conn.commit()
        return food_id
    finally:
        conn.close()
