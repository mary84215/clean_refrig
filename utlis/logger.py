import logging
from datetime import date
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

_configured = False


class DailyFileHandler(logging.FileHandler):
    """每天寫到 logs/log_yyyy-mm-dd.log，跨日時自動換檔"""

    def __init__(self, log_dir: Path = LOG_DIR):
        """建立 handler，並開啟今天的 log 檔

        Args:
            log_dir: 存放 log 檔的資料夾，不存在會自動建立

        Return:
            None
        """
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_date = date.today()
        super().__init__(self._path_for(self.current_date), encoding="utf-8", delay=True)

    def _path_for(self, day: date) -> Path:
        """取得指定日期的 log 檔路徑

        Args:
            day: 日期

        Return:
            Path: logs/log_yyyy-mm-dd.log
        """
        return self.log_dir / f"log_{day.isoformat()}.log"

    def emit(self, record: logging.LogRecord) -> None:
        """寫入一筆 log；日期變了就先關掉舊檔，改寫新日期的檔案

        Args:
            record: 要寫入的 log 紀錄

        Return:
            None
        """
        today = date.today()
        if today != self.current_date:
            self.acquire()
            try:
                self.close()
                self.current_date = today
                self.baseFilename = str(self._path_for(today))
            finally:
                self.release()
        super().emit(record)


def get_logger(name: str) -> logging.Logger:
    """取得模組用的 logger；全專案統一從這裡取得，格式與輸出由 setup_logging 決定

    Args:
        name: logger 名稱，一律傳入 __name__

    Return:
        logging.Logger: 該模組的 logger
    """
    return logging.getLogger(name)


def setup_logging(level: int = logging.INFO) -> None:
    """設定全專案的 log：統一格式，輸出到終端機並寫入每日 log 檔；重複呼叫不會重複設定

    Args:
        level: 要記錄的最低等級，預設 INFO

    Return:
        None
    """
    global _configured
    if _configured:
        return

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = DailyFileHandler()
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # uvicorn 的 logger 不會往上傳到 root，另外掛 file handler 才會寫進檔案（終端機仍由 uvicorn 自己印）
    for name in ("uvicorn", "uvicorn.access"):
        logging.getLogger(name).addHandler(file_handler)

    _configured = True
