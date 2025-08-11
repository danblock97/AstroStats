import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from core.client import run_bot

# Configure logging with safe file handler
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, log_level, logging.INFO))

formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

# Always log to console
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)

# Optionally log to file with rotation; disable if not writable
if os.getenv("LOG_TO_FILE", "1") not in {"0", "false", "False"}:
    try:
        file_handler = RotatingFileHandler(
            "bot.log",
            maxBytes=1_000_000,  # ~1 MB
            backupCount=3,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError:
        # Fall back to console-only logging if file is not writable
        pass

# Reduce exception spew from logging backend in constrained environments
logging.raiseExceptions = False

# Suppress noisy loggers
logging.getLogger("discord.gateway").setLevel(logging.ERROR)
logging.getLogger("discord.client").setLevel(logging.ERROR)
logging.getLogger("topgg").setLevel(logging.CRITICAL)

def main():
    """Main entry point for the bot."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logging.info("Bot shutting down...")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()