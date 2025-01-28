import logging
import os

# Define a PII log level
PII_LOG_LEVEL = 5
logging.addLevelName(PII_LOG_LEVEL, "PII")


def pii(self, message, *args, **kwargs):
    if self.isEnabledFor(PII_LOG_LEVEL):
        self._log(PII_LOG_LEVEL, message, args, **kwargs)


logging.Logger.pii = pii
logging.pii = lambda msg, *args, **kwargs: logging.log(
    PII_LOG_LEVEL, msg, *args, **kwargs)


def configure_logging():
    """
    Configures logging based on environment variables.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    pii_logging_enabled = os.getenv("PII_LOGGING_ENABLED",
                                    "false").lower() == "true"

    level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(level=level)

    if pii_logging_enabled:
        logging.warning("Environment Unicorn: PII logging enabled!")
        logging.getLogger().setLevel(PII_LOG_LEVEL)  # Lower log level to PII
    else:
        logging.info("Environment Pegasus: PII logging is disabled.")
