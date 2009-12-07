# Setup logging globally (ie root logger)
import types
import logging
import logging.handlers
import platform

INFO_NO_NEWLINE = logging.INFO + 1

class MultipleFormatHandler(logging.StreamHandler):

    formatters = {  logging.INFO: logging.Formatter(">>> %(message)s\n"),
                    INFO_NO_NEWLINE: logging.Formatter(">>> %(message)s"),
                    logging.DEBUG: logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s\n"),
                    logging.WARN: logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s\n"),
                    logging.CRITICAL: logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s\n"),
                    logging.ERROR: logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s\n")}

    def format(self,record):
        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        try:
            msg = self.format(record)
            fs = "%s"
            if not hasattr(types, "UnicodeType"): #if no unicode support...
                self.stream.write(fs % msg)
            else:
                try:
                    self.stream.write(fs % msg)
                except UnicodeError:
                    self.stream.write(fs % msg.encode("UTF-8"))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

log = logging.getLogger('starcluster')
log.setLevel(logging.INFO)

mfh = MultipleFormatHandler()
log.addHandler(mfh)

if platform.system() == "Linux":
    import os
    log_device = '/dev/log'
    if os.path.exists(log_device):
        log.debug("Logging to %s" % log_device)
        syslog_handler = logging.handlers.SysLogHandler(address=log_device)
        formatter = logging.Formatter("%(filename)s:%(lineno)d - %(levelname)s - %(message)s\n")
        syslog_handler.setFormatter(formatter)
        log.addHandler(syslog_handler)
