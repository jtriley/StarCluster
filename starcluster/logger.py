# Setup logging globally (ie root logger)
import logging

class MultipleFormatHandler(logging.StreamHandler):
    formatters = {  logging.INFO: logging.Formatter("%(levelname)s - %(message)s"),
                    logging.DEBUG: logging.Formatter("DEBUG %(filename)s:%(lineno)d - %(levelname)s - %(message)s"),
                    logging.WARN: logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s"),
                    logging.CRITICAL: logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s"),
                    logging.ERROR: logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s")}

    def format(self,record):
        return self.formatters[record.levelno].format(record)

logger = logging.getLogger('starcluster')
logger.setLevel(logging.DEBUG)
mfh = MultipleFormatHandler()
mfh.setLevel(logging.DEBUG)
logger.addHandler(mfh)
