
# Caddy Log Processor

A high-performance, asynchronous log processor for Caddy. It ingests logs via TCP, filters them based on customizable rules per site, stores them in SQLite, and provides real-time alerts and file management via a Telegram Bot.

## Features

* **Async Ingestion:** Uses AnyIO for non-blocking TCP log streaming.
* **Threaded Storage:** Writes to SQLite in a dedicated thread to ensure data integrity without blocking network I/O.
* **Dynamic Filtering:** Configurable rules for "Important" and "Very Important" logs based on HTTP method, status code, or URL path.
* **Hot-Swapping:** Automatically rotates and sends database files when row limits are reached or critical logs occur.
* **Telegram Integration:** Receive real-time alerts, log previews, and database files.
* **Remote Management:** Reload configuration, check health, and request database snapshots via bot commands.

## Requirements

* Python 3.9+
* Caddy Web Server
* Dependencies: `anyio`, `aiogram` (and an async backend like `trio` or `asyncio`)

## Installation

1. Clone the repository.
2. Install dependencies:
```bash
pip install anyio aiogram

```



## Configuration

### 1. Python Application

Create a `config.py` file in the root directory:

```python
# config.py
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_ID = 123456789  # Your numeric Telegram User ID

```

Create a `rules.json` file for site-specific logic:

```json
{
  "example.com": {
    "important_methods": ["POST", "PUT", "DELETE"],
    "important_paths": ["/login", "/api"],
    "very_important_methods": ["POST"],
    "very_important_paths": ["/admin", "/env"]
  }
}

```

### 2. Caddy Setup

Configure Caddy to send logs to this processor via TCP. Add this to your `Caddyfile`:

```caddyfile
example.com {
    log {
        output net tcp 127.0.0.1:9000
        format json
    }
    reverse_proxy localhost:8080
}

```

## Usage

Start the processor:

```bash
python main.py

```

### Bot Commands

* `/health` - View system uptime, active sites, and pending log counts.
* `/stats` - View detailed row counts for all active sites.
* `/getdb <site>` - Receive a non-destructive snapshot of the current database for a specific site.
* `/rotate <site>` - Force rotation of the current database file and receive it immediately.
* `/reload` - Hot-reload `rules.json` without restarting the service or dropping connections.

## Project Structure

* `main.py` - Application entry point and Task Group management.
* `core/server.py` - Async TCP server and log ingestion.
* `core/database.py` - Threaded SQLite worker and file rotation logic.
* `core/bot.py` - Telegram bot command handling and file sender.
* `core/processing.py` - Log parsing and filtering logic.
* `utils/` - Logging and crash reporting utilities.