import logging
logger = logging.getLogger("LLMHelper")

base_logger = logging.getLogger("LLMHelper")
base_logger.setLevel(logging.DEBUG)

class LLMHelperAdapter(logging.LoggerAdapter):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def process(self, msg, kwargs):
        return f"LLMHelper:{msg}", kwargs
    
    def isEnabledFor(self, level: int) -> bool:
        return self.logger.isEnabledFor(level)

logger = LLMHelperAdapter(base_logger, {})
