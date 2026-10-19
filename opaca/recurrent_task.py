import inspect
import logging
import asyncio
import uuid
import traceback
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Callable


log = logging.getLogger(__name__)


class RecurrentTask(BaseModel):
    task_id: str
    interval: timedelta
    run_immediately: bool
    callback: Callable

    is_running: bool = False
    start_time: datetime | None = None
    next_run: datetime | None = None

    async def start(self) -> None:
        self.start_time: datetime = datetime.now()
        self.is_running = True

        if self.run_immediately:
            await self.run()

        self.update_next_run()
        while self.is_running and self.start_time is not None and self.next_run is not None:
            await self.sleep()
            await self.run()
            self.update_next_run()

    async def cancel(self) -> None:
        self.is_running = False

    async def sleep(self) -> None:
        if self.start_time is None or self.next_run is None:
            return
        wait_time = (self.next_run - datetime.now()).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(wait_time)

    async def run(self) -> None:
        callback = self.callback
        if inspect.iscoroutinefunction(callback):
            callback = asyncio.to_thread(callback)

        try:
            asyncio.run(callback)
        except Exception as e:
            log.error(f'Recurrent task {self.task_id} failed: {e}')
            log.error(f'{traceback.format_exception(e)}')


    def update_next_run(self) -> None:
        self.next_run = _calc_next_run(self.start_time, self.interval)


def _calc_next_run(start_time: datetime, interval: timedelta) -> datetime:
    now = datetime.now()
    completed = (now - start_time) // interval
    return start_time + (completed + 1) * interval