import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Callable, Coroutine, Any

log = logging.getLogger(__name__)


@dataclass
class RecurrentTask:
    task_id: str
    interval: timedelta
    run_immediately: bool
    callback: Callable[[], Coroutine[Any, Any, None]]

    start_time: datetime | None = None
    next_run: datetime | None = None
    asyncio_task: asyncio.Task | None = None

    @property
    def is_running(self):
        if not self.asyncio_task:
            return False
        return not self.asyncio_task.done()

    async def start(self) -> None:
        self.start_time: datetime = datetime.now(tz=UTC)
        self.next_run: datetime = self.start_time + self.interval

        if self.run_immediately:
            await self.exec_callback()

        while self.is_running:
            await self.sleep()
            await self.exec_callback()
            self.update_next_run()

    def cancel(self) -> None:
        if self.asyncio_task is not None:
            self.asyncio_task.cancel()

    async def sleep(self) -> None:
        wait_time = (self.next_run - datetime.now()).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(wait_time)

    async def exec_callback(self) -> None:
        try:
            await self.callback()
        except Exception:
            log.exception(f'Recurrent task {self.task_id} failed.')

    def update_next_run(self) -> None:
        self.next_run += self.interval
        now = datetime.now()
        if self.next_run <= now:
            remaining = (now - self.next_run) // self.interval + 1
            self.next_run += remaining * self.interval


def start_tasks(tasks: dict[str, RecurrentTask]) -> None:
    for task_id, task in tasks.items():
        task.asyncio_task = asyncio.create_task(task.start(), name=task_id)
