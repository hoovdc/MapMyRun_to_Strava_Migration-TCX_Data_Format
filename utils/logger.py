import logging
import os
import warnings
from datetime import datetime

def setup_logger(level=logging.DEBUG):
    """Setup the root logger with a timed file handler."""
    # --- Custom Warning Handling ---
    # 1. Filter out the specific, noisy DeprecationWarning from stravalib/units.
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*You are using a Quantity object.*")

    # 2. Route all other warnings through the logging system.
    logging.captureWarnings(True)
    
    # 3. Define a custom format that avoids duplicating the "WARNING" prefix.
    def custom_format_warning(message, category, filename, lineno, line=None):
        return f"{category.__name__}: {message}"
    
    warnings.formatwarning = custom_format_warning

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

    # Suppress noisy INFO logs from the stravalib library during polling
    logging.getLogger("stravalib").setLevel(logging.WARNING)

    return logger 