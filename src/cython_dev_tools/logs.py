"""
Based on YAUBER-Executor project MIT licence

https://github.com/alexveden/yauber-executor
"""

import logging
import os
from .settings import CYTHON_TOOLS_LOG_PATH, CYTHON_TOOLS_LOG_FNAME


TRACE = 5
logging.addLevelName(TRACE, 'TRACE')
setattr(logging, 'TRACE', TRACE)

class YaUberLogger(logging.Logger):
    TRACE = TRACE
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARN = logging.WARNING
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __init__(self, global_log_name, log_base_dir=None, log_level=TRACE, log_level_file=None):
        super().__init__(global_log_name)

        self.logger_name = global_log_name
        self.logger = self

        #
        # Global settings
        #
        self.base_dir = log_base_dir
        self.log_level = log_level
        self.setup()

    def setup(self, name=None, log_base_dir=None, log_level=None, file_mode='a', verbosity=None):
        self.logger_name = self.logger_name if name is None else name
        if verbosity is None:
            self.log_level = self.log_level if log_level is None else log_level
        else:
            if verbosity < 0:
                self.log_level = logging.CRITICAL
            elif verbosity == 0:
                self.log_level = logging.ERROR
            elif verbosity == 1:
                self.log_level = logging.INFO
            elif verbosity == 2:
                self.log_level = logging.DEBUG
            else:
                self.log_level = TRACE

        if log_base_dir:
            self.base_dir = log_base_dir
            os.makedirs(os.path.join(self.base_dir), exist_ok=True)

        for hdlr in self.logger.handlers[:]:
            try:
                # Closing file descriptors for logs
                if isinstance(hdlr, logging.FileHandler):
                    hdlr.stream.close()
            except:
                pass

            self.logger.removeHandler(hdlr)

        formatter = logging.Formatter(fmt=f'%(asctime)s [{self.logger_name}] %(levelname)5s - %(message)s')

        if self.base_dir:
            handler_file = logging.FileHandler(os.path.join(self.base_dir,
                                                            f'{self.logger_name}.log'),
                                               mode=file_mode
                                               )
            handler_file.setFormatter(formatter)
            handler_file.setLevel(self.log_level)
            self.logger.addHandler(handler_file)

        handler_console = logging.StreamHandler()
        handler_console.setFormatter(formatter)
        handler_console.setLevel(self.log_level)
        self.logger.addHandler(handler_console)

        self.logger.setLevel(TRACE)

    def trace(self, msg, *args, **kwargs):
        # Use private method to correctly return the correct line number
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)


log = YaUberLogger(CYTHON_TOOLS_LOG_FNAME, log_base_dir=CYTHON_TOOLS_LOG_PATH)
