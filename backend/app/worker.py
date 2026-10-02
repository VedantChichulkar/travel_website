"""Dedicated process entry point for the existing idempotent operations loop."""

import asyncio
import logging
import signal

from app.core.logging_config import setup_logging
from app.services.operations_scheduler import run


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop.set)
        except NotImplementedError:
            pass
    logger.info("Maharashtra Tourist Places operations worker started")
    await run(stop)
    logger.info("Maharashtra Tourist Places operations worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
