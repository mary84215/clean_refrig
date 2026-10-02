import pymysql

from configs.configs import DB_CONFIG
from model.food import ExpireSoonFood


def query_expire_soon_food(user_id: str | None = None) -> list[ExpireSoonFood]:
    """查詢快過期（含已過期）的食物：有效期限距今天數 <= 到期前提醒天數

    Args:
        user_id: 只查這位使用者；None 表示查全部使用者

    Return:
        list[ExpireSoonFood]: 依 user_id、有效期限排序的食物清單
    """
    # DATEDIFF 回傳相差天數；直接 valid_date - NOW() 是 DATE 減 DATETIME，得到的不是天數
    sql = (
        "SELECT user_id, category, food_name, valid_date, days_left_to_notify "
        "FROM food WHERE DATEDIFF(valid_date, CURDATE()) <= days_left_to_notify"
    )
    params: tuple = ()
    if user_id is not None:
        sql += " AND user_id = %s"
        params = (user_id,)
    sql += " ORDER BY user_id, valid_date"

    conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    finally:
        conn.close()
    return [ExpireSoonFood.model_validate(row) for row in rows]
