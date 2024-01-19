import logging


def file_logger(log_file_path=None):
    if log_file_path is not None:
        logger = logging.getLogger(log_file_path.split("/")[-1])
    else:
        logger = logging.getLogger(__name__)

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if logger.hasHandlers():
        return logger

    if log_file_path:
        # Create a file handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # No file handler provided, log to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
