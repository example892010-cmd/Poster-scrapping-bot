import asyncio
import logging
import os
from urllib.parse import urlsplit

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from app.handlers import poster, start, templates

DEFAULT_PORT = 10000


def get_http_port() -> int:
    """Return Render's PORT value, with a safe local-development fallback."""
    raw_port = os.getenv("PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    return port if 1 <= port <= 65535 else DEFAULT_PORT


def create_dispatcher() -> Dispatcher:
    """Build the one dispatcher used by the bot's one polling loop."""
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(start.router)
    dispatcher.include_router(templates.router)
    dispatcher.include_router(poster.router)
    return dispatcher


async def health_request_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Serve a minimal HTTP/1.1 response for Render health checks."""
    try:
        request = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        request_line = request.split(b"\r\n", 1)[0].decode("latin-1")
        method, target, _ = request_line.split(" ", 2)
        path = urlsplit(target).path

        if method == "GET" and path in {"/", "/health"}:
            status = "200 OK"
            body = b'{"status":"ok"}\n'
        else:
            status = "404 Not Found"
            body = b'{"status":"not found"}\n'

        response = (
            f"HTTP/1.1 {status}\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("ascii") + body
        writer.write(response)
        await writer.drain()
    except (asyncio.IncompleteReadError, asyncio.TimeoutError, ValueError):
        # A malformed or disconnected health-check request should not stop the server.
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionError:
            pass


async def start_health_server(host: str = "0.0.0.0", port: int | None = None) -> asyncio.Server:
    """Start the HTTP server and return it so callers can close it cleanly."""
    bind_port = get_http_port() if port is None else port
    return await asyncio.start_server(health_request_handler, host=host, port=bind_port)


async def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is required")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = create_dispatcher()
    health_server = await start_health_server()
    polling_task = asyncio.create_task(
        dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    )

    logging.info("Health server listening on %s", ", ".join(str(sock.getsockname()) for sock in health_server.sockets or []))
    try:
        # The HTTP server accepts requests in the background while this single task
        # owns the bot's only polling loop.
        await polling_task
    finally:
        if not polling_task.done():
            polling_task.cancel()
            await asyncio.gather(polling_task, return_exceptions=True)
        health_server.close()
        await health_server.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
