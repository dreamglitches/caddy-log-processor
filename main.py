# main.py
import sys
import anyio
from core.server import start_server
from core.database import DBWorker
from core.bot import start_bot, setup_bot, file_sender_loop
from utils.logger import log_event, log_error
from utils.crash_reporter import send_crash_alert


async def main():
    # 1. Start DB Thread
    db_worker = DBWorker(rotate_limit=1000)
    db_worker.start()

    # 2. Setup Bot References
    setup_bot(db_worker)

    try:
        log_event("🚀 Caddy Log Processor Starting...")
        async with anyio.create_task_group() as tg:
            # Task A: TCP Server
            tg.start_soon(start_server, db_worker)

            # Task B: Bot Polling (Receiving Commands)
            tg.start_soon(start_bot)

            # Task C: Bot File Sender (Sending DBs)
            tg.start_soon(file_sender_loop)

    except KeyboardInterrupt:
        log_event("User stopped the program.")
    finally:
        log_event("Shutting down...")
        db_worker.stop()
        db_worker.join()
        await anyio.sleep(0.5)  # Give asyncio a moment to cleanup


if __name__ == "__main__":
    try:
        anyio.run(main)
    except Exception as e:
        # This catches crashes in the event loop itself or unhandled startup errors
        log_error("Fatal Error", exc_info=True)
        send_crash_alert(e)
        sys.exit(1)
