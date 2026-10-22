import asyncio

import main


async def request(server: asyncio.Server, path: str) -> tuple[str, bytes]:
    sock = server.sockets[0].getsockname()
    reader, writer = await asyncio.open_connection(sock[0], sock[1])
    writer.write(f"GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode())
    await writer.drain()
    response = await reader.read()
    writer.close()
    await writer.wait_closed()
    headers, body = response.split(b"\r\n\r\n", 1)
    return headers.decode("latin-1"), body


def test_root_and_health_return_200_and_status():
    async def run():
        server = await main.start_health_server(host="127.0.0.1", port=0)
        try:
            for path in ("/", "/health"):
                headers, body = await request(server, path)
                assert "HTTP/1.1 200 OK" in headers
                assert body == b'{"status":"ok"}\n'
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(run())


def test_server_binds_to_configured_port(monkeypatch):
    async def run():
        server = await main.start_health_server()
        try:
            assert server.sockets[0].getsockname()[1] == 18765
        finally:
            server.close()
            await server.wait_closed()

    monkeypatch.setenv("PORT", "18765")
    asyncio.run(run())


def test_port_falls_back_for_invalid_values(monkeypatch):
    monkeypatch.setenv("PORT", "not-a-port")
    assert main.get_http_port() == main.DEFAULT_PORT


def test_dispatcher_includes_existing_routers():
    dispatcher = main.create_dispatcher()
    assert dispatcher.sub_routers == [main.start.router, main.templates.router, main.poster.router]


def test_main_starts_one_polling_loop_and_closes_health_server(monkeypatch):
    events = []

    class FakeSession:
        async def close(self):
            events.append("session.close")

    class FakeBot:
        def __init__(self, *args, **kwargs):
            self.session = FakeSession()

    class FakeDispatcher:
        def resolve_used_update_types(self):
            return []

        async def start_polling(self, bot, allowed_updates):
            events.append(("polling", bot, allowed_updates))

    class FakeServer:
        sockets = []

        def close(self):
            events.append("server.close")

        async def wait_closed(self):
            events.append("server.wait_closed")

    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setattr(main, "Bot", FakeBot)
    monkeypatch.setattr(main, "create_dispatcher", FakeDispatcher)
    monkeypatch.setattr(main, "start_health_server", lambda: asyncio.sleep(0, result=FakeServer()))

    asyncio.run(main.main())

    assert [event[0] if isinstance(event, tuple) else event for event in events] == [
        "polling", "server.close", "server.wait_closed", "session.close"
    ]
