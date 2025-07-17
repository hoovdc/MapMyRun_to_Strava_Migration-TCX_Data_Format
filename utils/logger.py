import logging
import os
from datetime import datetime

def setup_logger(level=logging.DEBUG):
    """Setup the root logger with a timed file handler."""
    # Create timestamp-based directories
    now = datetime.now()
    year_month = now.strftime('%Y-%m')
    day_hour = now.strftime('%d-%H00') # This was month_day before, corrected for clarity
    log_dir = os.path.join('logs', year_month, now.strftime('%m-%d'), day_hour)
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f'{now.strftime("%H%M")}.log')

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Avoid adding duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler - logs everything from DEBUG level and up
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler - logs INFO, WARNING, ERROR, CRITICAL
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger 