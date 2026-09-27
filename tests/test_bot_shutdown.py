"""Stage 5 item C: SIGTERM/SIGINT must lead to orderly scheduler shutdown.

aiogram's Dispatcher already installs SIGTERM/SIGINT handlers around
dp.start_polling() and runs dp.shutdown hooks as soon as polling stops (see
aiogram.dispatcher.dispatcher.Dispatcher.start_polling). bot.py registers
stop_scheduler_on_shutdown as one such hook so the scheduler is told to stop at
that point too, rather than only after start_polling fully returns.
"""
import asyncio

from apscheduler.schedulers.base import STATE_RUNNING, STATE_STOPPED

import bot
from scheduler import scheduler


def test_stop_scheduler_on_shutdown_stops_a_running_scheduler(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "state", STATE_RUNNING)
    monkeypatch.setattr(scheduler, "shutdown", lambda wait=True: calls.append(wait))

    asyncio.run(bot.stop_scheduler_on_shutdown())

    assert calls == [False]  # cancels rather than waiting for in-flight work


def test_stop_scheduler_on_shutdown_is_a_noop_when_not_running(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "state", STATE_STOPPED)
    monkeypatch.setattr(scheduler, "shutdown", lambda wait=True: calls.append(wait))

    asyncio.run(bot.stop_scheduler_on_shutdown())

    assert calls == []


def test_main_registers_shutdown_hook_before_polling(monkeypatch):
    """main() must register the scheduler-stop hook on dp.shutdown before polling
    starts, not only rely on its own finally block (which only runs after
    dp.start_polling() has already finished aiogram's own shutdown sequence)."""
    import types

    registered = []

    class _FakeShutdownObserver:
        def register(self, callback):
            registered.append(callback)

    class _FakeDispatcher:
        def __init__(self, storage=None):
            self.shutdown = _FakeShutdownObserver()
            self.include_router_calls = []

        def include_router(self, router):
            self.include_router_calls.append(router)

        async def start_polling(self, bot_instance):
            # By the time polling would run, the hook must already be registered.
            assert bot.stop_scheduler_on_shutdown in registered

    class _FakeBot:
        def __init__(self, token):
            self.token = token
            self.session = types.SimpleNamespace(close=_noop)

    async def _noop(*_a, **_k):
        return None

    async def fake_init_db():
        return None

    async def fake_run_outputs_cleanup():
        return None

    def fake_get_settings():
        return types.SimpleNamespace(bot_token="test-token")

    def fake_setup_scheduler(bot_instance):
        return None

    monkeypatch.setattr(bot, "Dispatcher", _FakeDispatcher)
    monkeypatch.setattr(bot, "Bot", _FakeBot)
    monkeypatch.setattr(bot, "init_db", fake_init_db)
    monkeypatch.setattr(bot, "run_outputs_cleanup", fake_run_outputs_cleanup)
    monkeypatch.setattr(bot, "get_settings", fake_get_settings)
    monkeypatch.setattr(bot, "setup_scheduler", fake_setup_scheduler)
    monkeypatch.setattr(bot, "setup_logging", lambda: None)
    monkeypatch.setattr(scheduler, "state", STATE_STOPPED)

    asyncio.run(bot.main())

    assert registered == [bot.stop_scheduler_on_shutdown]
