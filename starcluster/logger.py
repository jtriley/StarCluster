"""
StarCluster logging module
"""
import os
import types
import logging
import logging.handlers
import textwrap
import StringIO

from starcluster import static

INFO = logging.INFO
DEBUG = logging.DEBUG
WARN = logging.WARN
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
FATAL = logging.FATAL

RAW_FORMAT = "%(message)s\n"
INFO_FORMAT = " ".join(['>>>', "%(message)s\n"])
_DEBUG_FORMAT = "%(filename)s:%(lineno)d - %(levelname)s - %(message)s\n"
DEBUG_FORMAT = "%(asctime)s " + _DEBUG_FORMAT
DEBUG_FORMAT_PID = ' '.join(["%(asctime)s", "PID: %s" % str(static.PID),
                             _DEBUG_FORMAT])
DEFAULT_CONSOLE_FORMAT = "%(levelname)s - %(message)s\n"
ERROR_CONSOLE_FORMAT = " ".join(['!!!', DEFAULT_CONSOLE_FORMAT])
WARN_CONSOLE_FORMAT = " ".join(['***', DEFAULT_CONSOLE_FORMAT])


class ConsoleLogger(logging.StreamHandler):

    formatters = {
        INFO: logging.Formatter(INFO_FORMAT),
        DEBUG: logging.Formatter(DEBUG_FORMAT),
        WARN: logging.Formatter(WARN_CONSOLE_FORMAT),
        ERROR: logging.Formatter(ERROR_CONSOLE_FORMAT),
        CRITICAL: logging.Formatter(ERROR_CONSOLE_FORMAT),
        FATAL: logging.Formatter(ERROR_CONSOLE_FORMAT),
        'raw': logging.Formatter(RAW_FORMAT),
    }

    def format(self, record):
        if hasattr(record, '__raw__'):
            result = self.formatters['raw'].format(record)
        else:
            result = self.formatters[record.levelno].format(record)
        if hasattr(record, '__nonewline__'):
            result = result.rstrip()
        return result

    def _wrap(self, msg):
        msg = textwrap.wrap(msg, width=60, replace_whitespace=False,
                            drop_whitespace=True, break_on_hyphens=False)
        return msg or ['']

    def _emit_textwrap(self, record):
        lines = []
        for line in record.msg.splitlines():
            lines.extend(self._wrap(line))
        if hasattr(record, '__nosplitlines__'):
            lines = ['\n'.join(lines)]
        for line in lines:
            record.msg = line
            self._emit(record)

    def _emit(self, record):
        msg = self.format(record)
        fs = "%s"
        if not hasattr(types, "UnicodeType"):
             # if no unicode support...
            self.stream.write(fs % msg)
        else:
            try:
                self.stream.write(fs % msg)
            except UnicodeError:
                self.stream.write(fs % msg.encode("UTF-8"))
        self.flush()

    def emit(self, record):
        try:
            if hasattr(record, '__textwrap__'):
                self._emit_textwrap(record)
            else:
                self._emit(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


def get_starcluster_logger():
    log = logging.getLogger('starcluster')
    log.addHandler(NullHandler())
    return log


log = get_starcluster_logger()
console = ConsoleLogger()
session = logging.StreamHandler(StringIO.StringIO())


def configure_sc_logging(use_syslog=False):
    """
    Configure logging for StarCluster *application* code

    By default StarCluster's logger has no formatters and a NullHandler so that
    other developers using StarCluster as a library can configure logging as
    they see fit. This method is used in StarCluster's application code (i.e.
    the 'starcluster' command) to toggle StarCluster's application specific
    formatters/handlers

    use_syslog - enable logging all messages to syslog. currently only works if
    /dev/log exists on the system (standard for most Linux distros)
    """
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(DEBUG_FORMAT_PID.rstrip())
    static.create_sc_config_dirs()
    rfh = logging.handlers.RotatingFileHandler(static.DEBUG_FILE,
                                               maxBytes=1048576,
                                               backupCount=2)
    rfh.setLevel(logging.DEBUG)
    rfh.setFormatter(formatter)
    log.addHandler(rfh)
    console.setLevel(logging.INFO)
    log.addHandler(console)
    session.setLevel(logging.DEBUG)
    session.setFormatter(formatter)
    log.addHandler(session)
    syslog_device = '/dev/log'
    if use_syslog and os.path.exists(syslog_device):
        log.debug("Logging to %s" % syslog_device)
        syslog_handler = logging.handlers.SysLogHandler(address=syslog_device)
        syslog_handler.setFormatter(formatter)
        syslog_handler.setLevel(logging.DEBUG)
        log.addHandler(syslog_handler)


def configure_paramiko_logging():
    """
    Configure paramiko to log to a file for debug
    """
    l = logging.getLogger("paramiko")
    l.setLevel(logging.DEBUG)
    static.create_sc_config_dirs()
    lh = logging.handlers.RotatingFileHandler(static.SSH_DEBUG_FILE,
                                              maxBytes=1048576,
                                              backupCount=2)
    lh.setLevel(logging.DEBUG)
    format = (('PID: %s ' % str(static.PID)) +
              '%(levelname)-.3s [%(asctime)s.%(msecs)03d] '
              'thr=%(_threadid)-3d %(name)s: %(message)s')
    date_format = '%Y%m%d-%H:%M:%S'
    lh.setFormatter(logging.Formatter(format, date_format))
    l.addHandler(lh)


def configure_boto_logging():
    """
    Configure boto to log to a file for debug
    """
    l = logging.getLogger("boto")
    l.setLevel(logging.DEBUG)
    static.create_sc_config_dirs()
    lh = logging.handlers.RotatingFileHandler(static.AWS_DEBUG_FILE,
                                              maxBytes=1048576,
                                              backupCount=2)
    lh.setLevel(logging.DEBUG)
    format = (('PID: %s ' % str(static.PID)) +
              '%(levelname)-.3s [%(asctime)s.%(msecs)03d] '
              '%(name)s: %(message)s')
    date_format = '%Y%m%d-%H:%M:%S'
    lh.setFormatter(logging.Formatter(format, date_format))
    l.addHandler(lh)
