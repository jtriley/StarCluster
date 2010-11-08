#!/usr/bin/env python
"""
StarCluster logging module
"""
import types
import logging
import logging.handlers

from starcluster import static

INFO = logging.INFO
DEBUG = logging.DEBUG
WARN = logging.WARN
ERROR = logging.ERROR
FATAL = logging.FATAL

INFO_NO_NEWLINE = logging.INFO + 1
INFO_FORMAT = ">>> %(message)s\n"
INFO_FORMAT_NONL = ">>> %(message)s"
DEFAULT_FORMAT = "%(filename)s:%(lineno)d - %(levelname)s - %(message)s\n"
DEFAULT_FORMAT_NONL = "%(filename)s:%(lineno)d - %(levelname)s - %(message)s"
DEFAULT_FORMAT_NONL_PID = ("PID: %s " % str(static.PID)) + DEFAULT_FORMAT_NONL


class ConsoleLogger(logging.StreamHandler):

    formatters = {
        logging.INFO: logging.Formatter(INFO_FORMAT),
        INFO_NO_NEWLINE: logging.Formatter(INFO_FORMAT_NONL),
        logging.DEBUG: logging.Formatter(DEFAULT_FORMAT),
        logging.WARN: logging.Formatter(DEFAULT_FORMAT),
        logging.CRITICAL: logging.Formatter(DEFAULT_FORMAT),
        logging.ERROR: logging.Formatter(DEFAULT_FORMAT),
    }

    def format(self, record):
        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        try:
            msg = self.format(record)
            fs = "%s"
            if not hasattr(types, "UnicodeType"):  # if no unicode support...
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
log.setLevel(logging.DEBUG)

formatter = logging.Formatter(DEFAULT_FORMAT_NONL_PID)

rfh = logging.handlers.RotatingFileHandler(static.DEBUG_FILE,
                                           maxBytes=1048576,
                                           backupCount=2)
rfh.setLevel(logging.DEBUG)
rfh.setFormatter(formatter)
log.addHandler(rfh)

console = ConsoleLogger()
console.setLevel(logging.INFO)
log.addHandler(console)

#import platform
#if platform.system() == "Linux":
    #import os
    #log_device = '/dev/log'
    #if os.path.exists(log_device):
        #log.debug("Logging to %s" % log_device)
        #syslog_handler = logging.handlers.SysLogHandler(address=log_device)
        #syslog_handler.setFormatter(formatter)
        #syslog_handler.setLevel(logging.DEBUG)
        #log.addHandler(syslog_handler)


def _configure_paramiko_logging():
    """
    Configure paramiko to log to a file for debug
    """
    l = logging.getLogger("paramiko")
    l.setLevel(logging.DEBUG)
    lh = logging.handlers.RotatingFileHandler(static.SSH_DEBUG_FILE,
                                               maxBytes=1048576,
                                               backupCount=2)
    lh.setLevel(logging.DEBUG)
    format = (('PID: %s ' % str(static.PID)) + \
              '%(levelname)-.3s [%(asctime)s.%(msecs)03d] ' + \
              'thr=%(_threadid)-3d %(name)s: %(message)s')
    date_format = '%Y%m%d-%H:%M:%S'
    lh.setFormatter(logging.Formatter(format, date_format))
    l.addHandler(lh)


def _configure_boto_logging():
    """
    Configure boto to log to a file for debug
    """
    l = logging.getLogger("boto")
    l.setLevel(logging.DEBUG)
    lh = logging.handlers.RotatingFileHandler(static.AWS_DEBUG_FILE,
                                               maxBytes=1048576,
                                               backupCount=2)
    lh.setLevel(logging.DEBUG)
    format = (('PID: %s ' % str(static.PID)) + \
              '%(levelname)-.3s [%(asctime)s.%(msecs)03d] ' + \
              '%(name)s: %(message)s')
    date_format = '%Y%m%d-%H:%M:%S'
    lh.setFormatter(logging.Formatter(format, date_format))
    l.addHandler(lh)
