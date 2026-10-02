# 建立 database 與 table，可重複執行：python -m utlis.init_db
from pathlib import Path

import pymysql

from configs.configs import DB_CONFIG

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def init_db() -> None:
    """建立 database 與 sql/schema.sql 內的 table，已存在則略過，可重複執行

    Args:
        無

    Return:
        None
    """
    db_name = DB_CONFIG["database"]
    server_config = {k: v for k, v in DB_CONFIG.items() if k != "database"}

    conn = pymysql.connect(**server_config)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4")
        conn.commit()
    finally:
        conn.close()

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            for statement in schema_sql.split(";"):
                if statement.strip():
                    cursor.execute(statement)
        conn.commit()
    finally:
        conn.close()

    print(f"Database `{db_name}` and tables are ready.")


if __name__ == "__main__":
    init_db()
