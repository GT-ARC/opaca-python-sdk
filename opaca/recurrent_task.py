import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Callable, Awaitable

log = logging.getLogger(__name__)


@dataclass
class RecurrentTask:
    """
    A class representing a recurrent task marked by the @every decorator.
    """

    task_id: str
    interval: timedelta
    run_immediately: bool
    callback: Callable[[], Awaitable[None]]

    next_run: datetime | None = None
    asyncio_task: asyncio.Task | None = None

    @property
    def is_running(self):
        if not self.asyncio_task:
            return False
        return not self.asyncio_task.done()

    def start(self) -> None:
        """
        Start this task. If it is already running, it is cancelled and then restarted.
        """
        self.cancel()
        self.asyncio_task: asyncio.Task = asyncio.create_task(self._run(), name=self.task_id)
        self.asyncio_task.add_done_callback(_log_task_exception)

    def cancel(self) -> None:
        """
        Cancel this task. If it has already been cancelled, do nothing.
        """
        if self.asyncio_task is not None:
            self.asyncio_task.cancel()

    async def _run(self) -> None:
        self.next_run: datetime = datetime.now(tz=UTC) + self.interval

        if self.run_immediately:
            await self._exec_callback()

        while self.is_running:
            await self._sleep()
            await self._exec_callback()
            self._update_next_run()

    async def _sleep(self) -> None:
        wait_time = (self.next_run - datetime.now(tz=UTC)).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(wait_time)

    async def _exec_callback(self) -> None:
        try:
            await self.callback()
        except Exception as e:
            log.error(f'Recurrent task {self.task_id!r} failed.', exc_info=e)

    def _update_next_run(self) -> None:
        self.next_run += self.interval
        now = datetime.now(tz=UTC)
        if self.next_run <= now:
            remaining = (now - self.next_run) // self.interval + 1
            self.next_run += remaining * self.interval


def _log_task_exception(atask: asyncio.Task) -> None:
    if not atask.cancelled() and atask.exception():
        log.error(f'Recurrent task {atask.get_name()!r} failed.', exc_info=atask.exception())
