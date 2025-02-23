import logging
from colorama import Fore, Style, Back

class Logger:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.logger = logging.getLogger("AzumiLogger")
            cls._instance.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(ColorFormatter())
            cls._instance.logger.addHandler(handler)

        return cls._instance

    def get_logger(self):
        return self.logger

class ColorFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: Back.WHITE + Style.BRIGHT + " %(asctime)s " + Back.CYAN + " DEBUG " + Style.RESET_ALL + Fore.LIGHTCYAN_EX + " %(message)s" + Style.RESET_ALL,
        logging.INFO: Back.WHITE + Style.BRIGHT + " %(asctime)s " + Back.GREEN + " INFO " + Style.RESET_ALL + Fore.LIGHTWHITE_EX + " %(message)s" + Style.RESET_ALL,
        logging.WARNING: Back.WHITE + Style.BRIGHT + " %(asctime)s " + Back.YELLOW + " WARNING " + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + " %(message)s" + Style.RESET_ALL,
        logging.ERROR: Back.WHITE + Style.BRIGHT + " %(asctime)s " + Back.RED + " ERROR " + Style.RESET_ALL + Fore.LIGHTRED_EX + " %(message)s" + Style.RESET_ALL,
        logging.CRITICAL: Back.WHITE + Style.BRIGHT + " %(asctime)s " + Back.RED + " CRITICAL " + Style.RESET_ALL + Fore.RED + " %(message)s" + Style.RESET_ALL,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(asctime)s - %(message)s")
        formatter = logging.Formatter(log_fmt, datefmt="%d.%m.%Y %H:%M:%S")
        return formatter.format(record)


def get_logger():
    return Logger().get_logger()
