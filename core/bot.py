# core/bot.py
import os
import time
import anyio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from config import BOT_TOKEN, ADMIN_ID
from core.database import DBWorker
from core.config_manager import config_manager
from utils.logger import log_event, log_error

# Initialize Bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
_start_time = time.time()

# Global reference to DB Worker for commands
_db_worker: DBWorker = None


def setup_bot(db_worker_instance):
    global _db_worker
    _db_worker = db_worker_instance


# --- Background Task: Send Files ---
async def file_sender_loop():
    """Watches the DB Worker queue and sends files to Telegram"""
    log_event("Bot File Sender Loop Started")
    while True:
        try:
            # Non-blocking check
            while not _db_worker.notification_queue.empty():
                item = _db_worker.notification_queue.get()
                site = item["site"]
                important_preview = item.get(
                    "important_preview"
                )  # Only important request preview no file sending
                if important_preview:
                    text = f"<b>🎯 Important req:</b> {site}\n\n"
                    text += important_preview
                    text += f"\n<pre>/getdb {site}</pre>"
                    try:
                        await bot.send_message(ADMIN_ID, text, parse_mode="HTML")

                    except Exception as e:
                        log_error(
                            f"Failed to send important preview- {important_preview}: {e}"
                        )
                    finally:
                        await anyio.sleep(1)  # Sleep to yield control
                        continue

                path = item["path"]
                reason = item["reason"]
                preview = item.get("preview")

                caption = f"📦 <b>Log Export:</b> {site}\n📝 <b>Reason:</b> {reason}"
                if preview:
                    caption += f"\n\n{preview}"

                file_input = FSInputFile(path)

                try:
                    await bot.send_document(
                        ADMIN_ID, file_input, caption=caption, parse_mode="HTML"
                    )
                    log_event(f"Sent file {path} to user")

                    if item.get("delete_after", True):
                        os.remove(path)
                        log_event(f"Deleted file {path}")

                except Exception as e:
                    log_error(f"Failed to send file {path}: {e}")

            await anyio.sleep(1)  # Sleep to yield control
        except Exception as e:
            log_error(f"Error in file sender loop: {e}")
            await anyio.sleep(5)


# --- Commands ---


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "👋 Caddy Log Processor Bot is Online!\n\n"
        "Commands:\n"
        "/stats - Show active sites and row counts\n"
        "/getdb <site> - Get current DB (snapshot)\n"
        "/rotate <site> - Force rotate and get DB\n"
        "/reload - Reload site configuration\n"
        "/health - System status\n"
    )


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    stats = _db_worker.get_active_sites()
    if not stats:
        await message.answer("No active sites currently tracking.")
        return

    text = "📊 <b>Live Statistics</b>\n\n"
    for site, count in stats.items():
        text += f"🔹 <b>{site}</b>: {count} rows pending\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("getdb"))
async def cmd_getdb(message: types.Message):
    """Usage: /getdb site1.com"""
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Usage: `/getdb <site_name>`")
        return

    site = args[1]
    _db_worker.request_snapshot(site)
    await message.answer(f"📸 Snapshot requested for {site}. Sending shortly...")


@dp.message(Command("rotate"))
async def cmd_rotate(message: types.Message):
    """Usage: /rotate site1.com"""
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Usage: `/rotate <site_name>`")
        return

    site = args[1]
    _db_worker.request_rotation(site)
    await message.answer(f"🔄 Force rotation requested for {site}...")


@dp.message(Command("reload"))
async def cmd_reload(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    success = config_manager.load_configs()
    if success:
        await message.answer(
            f"✅ Configuration reloaded! Active sites: {len(config_manager.configs)}"
        )
    else:
        await message.answer("❌ Failed to reload configuration. Check logs.")


@dp.message(Command("health"))
async def cmd_health(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    # Calculate Uptime
    uptime_sec = int(time.time() - _start_time)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    # Get DB Stats
    stats = _db_worker.get_active_sites()
    total_sites = len(stats)
    total_pending = sum(stats.values())

    text = (
        f"🏥 <b>System Health</b>\n"
        f"⏱ <b>Uptime:</b> {uptime_str}\n"
        f"🌐 <b>Active Sites:</b> {total_sites}\n"
        f"📥 <b>Pending Logs:</b> {total_pending}\n"
        f"⚙️ <b>Service:</b> Running"
    )
    await message.answer(text, parse_mode="HTML")


async def start_bot():
    # Start polling
    await dp.start_polling(bot)
