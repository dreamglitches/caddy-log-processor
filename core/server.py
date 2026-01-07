import anyio
import json
from core.processing import CaddyLog
from core.config_manager import config_manager
from utils.logger import log_event, log_error
from core.database import DBWorker

db_worker_ref: DBWorker = None


async def handle_log_line(line: bytes):
    try:
        data = json.loads(line)
        host = data.get("request", {}).get("host", "unknown")
        if ":" in host:
            host = host.split(":")[0]

        # 1. Use ConfigManager
        config = config_manager.get_config(host)
        log_obj = CaddyLog(data, config)

        preview_text = None
        is_vip = log_obj.is_very_important

        # 2. Generate Preview if VIP
        if is_vip:
            preview_text = log_obj.get_preview_string()
            log_event(f"!!! VIP [{host}]: {log_obj.status} {log_obj.uri}")
        elif log_obj.is_important:
            log_event(f"* IMP [{host}]: {log_obj.method}")
        else:
            return  # Discard

        if db_worker_ref:
            # 3. Pass 'preview' to DB Worker
            db_worker_ref.input_queue.put(
                {
                    "type": "log",
                    "site": host,
                    "data": log_obj.to_tuple(),
                    "vip": is_vip,
                    "preview": preview_text,
                }
            )

    except Exception as e:
        log_error(f"Error processing log line: {e}", exc_info=True)


async def handle_connection(stream: anyio.abc.ByteStream):
    # Same as Phase 1 ...
    async with stream:
        buffer = b""
        async for chunk in stream:
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line:
                    await handle_log_line(line)


async def start_server(db_worker: DBWorker, host="0.0.0.0", port=9000):
    global db_worker_ref
    db_worker_ref = db_worker  # Store reference for handlers

    listener = await anyio.create_tcp_listener(local_host=host, local_port=port)
    log_event(f"TCP Log Server listening on {host}:{port}")
    await listener.serve(handle_connection)
