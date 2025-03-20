import logging
from datetime import datetime


def setup_custom_logger() -> logging.Logger:
    format = "%(asctime)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    log_filename = datetime.now().strftime("%Y-%m-%d-%s.log")
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setFormatter(formatter)

    l = logging.getLogger()

    l.addHandler(stream_handler)
    l.addHandler(file_handler)
    l.setLevel(logging.INFO)
    return l
