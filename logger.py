import logging
import os
from datetime import datetime


def setup_logger(log_file="trade_log.txt"):
    """Set up a logger that writes to both console and a file."""
    logger = logging.getLogger("XAUUSDBot")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_format)

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def log_trade(log_file, action, symbol, volume, price, sl, tp, result_comment=""):
    """Append a trade record to the trade log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"{timestamp} | {action:5s} | {symbol} | "
        f"Vol: {volume:.2f} | Price: {price:.2f} | "
        f"SL: {sl:.2f} | TP: {tp:.2f} | {result_comment}\n"
    )
    with open(log_file, "a") as f:
        f.write(line)
