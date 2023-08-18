from __future__ import annotations

import asyncio
import datetime
from typing import (
    Any,
    Callable,
    Coroutine,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)


import inspect

from collections.abc import Sequence

from .backoff import ExponentialBackoff


from loguru import logger

# fmt: off
__all__ = (
    'loop',
)
# fmt: on

T = TypeVar('T')
_func = Callable[..., Coroutine[Any, Any, Any]]
LF = TypeVar('LF', bound=_func)
FT = TypeVar('FT', bound=_func)
ET = TypeVar('ET', bound=Callable[[Any, BaseException], Coroutine[Any, Any, Any]])


def compute_timedelta(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.astimezone()
    now = datetime.datetime.now(datetime.timezone.utc)
    return max((dt - now).total_seconds(), 0)

def is_ambiguous(dt: datetime.datetime) -> bool:
    if dt.tzinfo is None or isinstance(dt.tzinfo, datetime.timezone):
        # Naive or fixed timezones are never ambiguous
        return False

    before = dt.replace(fold=0)
    after = dt.replace(fold=1)

    same_offset = before.utcoffset() == after.utcoffset()
    same_dst = before.dst() == after.dst()
    return not (same_offset and same_dst)


def is_imaginary(dt: datetime.datetime) -> bool:
    if dt.tzinfo is None or isinstance(dt.tzinfo, datetime.timezone):
        # Naive or fixed timezones are never imaginary
        return False

    tz = dt.tzinfo
    dt = dt.replace(tzinfo=None)
    roundtrip = dt.replace(tzinfo=tz).astimezone(datetime.timezone.utc).astimezone(tz).replace(tzinfo=None)
    return dt != roundtrip


def resolve_datetime(dt: datetime.datetime) -> datetime.datetime:
    if dt.tzinfo is None or isinstance(dt.tzinfo, datetime.timezone):
        # Naive or fixed requires no resolution
        return dt

    if is_imaginary(dt):
        # Largest gap is probably 24 hours
        tomorrow = dt + datetime.timedelta(days=1)
        yesterday = dt - datetime.timedelta(days=1)
        # utcoffset shouldn't return None since these are aware instances
        # If it returns None then the timezone implementation was broken from the get go
        return dt + (tomorrow.utcoffset() - yesterday.utcoffset())  # type: ignore
    elif is_ambiguous(dt):
        return dt.replace(fold=1)
    else:
        return dt


class SleepHandle:
    __slots__ = ('future', 'loop', 'handle')

    def __init__(self, dt: datetime.datetime, *, loop: asyncio.AbstractEventLoop) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        self.future: asyncio.Future[None] = loop.create_future()
        relative_delta = compute_timedelta(dt)
        self.handle = loop.call_later(relative_delta, self.future.set_result, True)

    def recalculate(self, dt: datetime.datetime) -> None:
        self.handle.cancel()
        relative_delta = compute_timedelta(dt)
        self.handle: asyncio.TimerHandle = self.loop.call_later(relative_delta, self.future.set_result, True)

    def wait(self) -> asyncio.Future[Any]:
        return self.future

    def done(self) -> bool:
        return self.future.done()

    def cancel(self) -> None:
        self.handle.cancel()
        self.future.cancel()


class Loop(Generic[LF]):
    def __init__(
        self,
        coro: LF,
        seconds: float,
        hours: float,
        minutes: float,
        time: Union[datetime.time, Sequence[datetime.time]],
        count: Optional[int],
        reconnect: bool,
        name: Optional[str],
    ) -> None:
        self.coro: LF = coro
        self.reconnect: bool = reconnect
        self.count: Optional[int] = count
        self._current_loop = 0
        self._handle: Optional[SleepHandle] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._injected = None
        self._valid_exception = (
            OSError,
            asyncio.TimeoutError,
        )

        self._before_loop = None
        self._after_loop = None
        self._is_being_cancelled = False
        self._has_failed = False
        self._stop_next_iteration = False
        self._name: str = f'discord-ext-tasks: {coro.__qualname__}' if name is None else name

        if self.count is not None and self.count <= 0:
            raise ValueError('count must be greater than 0 or None.')

        self.change_interval(seconds=seconds, minutes=minutes, hours=hours, time=time)
        self._last_iteration_failed = False
        self._last_iteration: datetime.datetime = None
        self._next_iteration = None

        if not inspect.iscoroutinefunction(self.coro):
            raise TypeError(f'Expected coroutine function, not {type(self.coro).__name__!r}.')

    async def _call_loop_function(self, name: str, *args: Any, **kwargs: Any) -> None:
        coro = getattr(self, '_' + name)
        if coro is None:
            return

        if self._injected is not None:
            await coro(self._injected, *args, **kwargs)
        else:
            await coro(*args, **kwargs)

    def _try_sleep_until(self, dt: datetime.datetime):
        self._handle = SleepHandle(dt=dt, loop=asyncio.get_running_loop())
        return self._handle.wait()

    def _is_relative_time(self) -> bool:
        return self._time is None

    def _is_explicit_time(self) -> bool:
        return self._time is not None

    async def _loop(self, *args: Any, **kwargs: Any) -> None:
        backoff = ExponentialBackoff()
        await self._call_loop_function('before_loop')
        self._last_iteration_failed = False
        if self._is_explicit_time():
            self._next_iteration = self._get_next_sleep_time()
        else:
            self._next_iteration = datetime.datetime.now(datetime.timezone.utc)
            await asyncio.sleep(0)  # allows canceling in before_loop
        try:
            if self._stop_next_iteration:  # allow calling stop() before first iteration
                return
            while True:
                # sleep before the body of the task for explicit time intervals
                if self._is_explicit_time():
                    await self._try_sleep_until(self._next_iteration)
                if not self._last_iteration_failed:
                    self._last_iteration = self._next_iteration
                    self._next_iteration = self._get_next_sleep_time()

                    # In order to account for clock drift, we need to ensure that
                    # the next iteration always follows the last iteration.
                    # Sometimes asyncio is cheeky and wakes up a few microseconds before our target
                    # time, causing it to repeat a run.
                    while self._is_explicit_time() and self._next_iteration <= self._last_iteration:
                        logger.warning(
                            (
                                'Clock drift detected for task %s. Woke up at %s but needed to sleep until %s. '
                                'Sleeping until %s again to correct clock'
                            ),
                            self.coro.__qualname__,
                            datetime.datetime.utcnow(),
                            self._next_iteration,
                            self._next_iteration,
                        )
                        await self._try_sleep_until(self._next_iteration)
                        self._next_iteration = self._get_next_sleep_time()

                try:
                    await self.coro(*args, **kwargs)
                    self._last_iteration_failed = False
                except self._valid_exception:
                    self._last_iteration_failed = True
                    if not self.reconnect:
                        raise
                    await asyncio.sleep(backoff.delay())
                else:
                    if self._stop_next_iteration:
                        return

                    # sleep after the body of the task for relative time intervals
                    if self._is_relative_time():
                        await self._try_sleep_until(self._next_iteration)

                    self._current_loop += 1
                    if self._current_loop == self.count:
                        break

        except asyncio.CancelledError:
            self._is_being_cancelled = True
            raise
        except Exception as exc:
            self._has_failed = True
            await self._call_loop_function('error', exc)
            raise exc
        finally:
            await self._call_loop_function('after_loop')
            if self._handle:
                self._handle.cancel()
            self._is_being_cancelled = False
            self._current_loop = 0
            self._stop_next_iteration = False

    def __get__(self, obj: T, objtype: Type[T]) -> Loop[LF]:
        if obj is None:
            return self

        copy: Loop[LF] = Loop(
            self.coro,
            seconds=self._seconds,
            hours=self._hours,
            minutes=self._minutes,
            time=self._time,
            count=self.count,
            reconnect=self.reconnect,
            name=self._name,
        )
        copy._injected = obj
        copy._before_loop = self._before_loop
        copy._after_loop = self._after_loop
        copy._error = self._error
        setattr(obj, self.coro.__name__, copy)
        return copy

    @property
    def seconds(self) -> Optional[float]:
        if self._seconds is not None:
            return self._seconds

    @property
    def minutes(self) -> Optional[float]:
        if self._minutes is not None:
            return self._minutes

    @property
    def hours(self) -> Optional[float]:
        if self._hours is not None:
            return self._hours

    @property
    def time(self) -> Optional[List[datetime.time]]:
        if self._time is not None:
            return self._time.copy()

    @property
    def current_loop(self) -> int:
        """:class:`int`: The current iteration of the loop."""
        return self._current_loop

    @property
    def next_iteration(self) -> Optional[datetime.datetime]:
        if self._task is None:
            return None
        elif self._task and self._task.done() or self._stop_next_iteration:
            return None
        return self._next_iteration

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._injected is not None:
            args = (self._injected, *args)

        return await self.coro(*args, **kwargs)

    def start(self, *args: Any, **kwargs: Any) -> asyncio.Task[None]:
        if self._task and not self._task.done():
            raise RuntimeError('Task is already launched and is not completed.')

        if self._injected is not None:
            args = (self._injected, *args)

        self._has_failed = False
        self._task = asyncio.create_task(self._loop(*args, **kwargs), name=self._name)
        return self._task

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._stop_next_iteration = True

    def _can_be_cancelled(self) -> bool:
        return bool(not self._is_being_cancelled and self._task and not self._task.done())

    def cancel(self) -> None:
        """Cancels the internal task, if it is running."""
        if self._can_be_cancelled() and self._task:
            self._task.cancel()

    def restart(self, *args: Any, **kwargs: Any) -> None:
        def restart_when_over(fut: Any, *, args: Any = args, kwargs: Any = kwargs) -> None:
            if self._task:
                self._task.remove_done_callback(restart_when_over)
            self.start(*args, **kwargs)

        if self._can_be_cancelled() and self._task:
            self._task.add_done_callback(restart_when_over)
            self._task.cancel()

    def add_exception_type(self, *exceptions: Type[BaseException]) -> None:
        for exc in exceptions:
            if not inspect.isclass(exc):
                raise TypeError(f'{exc!r} must be a class.')
            if not issubclass(exc, BaseException):
                raise TypeError(f'{exc!r} must inherit from BaseException.')

        self._valid_exception = (*self._valid_exception, *exceptions)

    def clear_exception_types(self) -> None:
        self._valid_exception = ()

    def remove_exception_type(self, *exceptions: Type[BaseException]) -> bool:
        old_length = len(self._valid_exception)
        self._valid_exception = tuple(x for x in self._valid_exception if x not in exceptions)
        return len(self._valid_exception) == old_length - len(exceptions)

    def get_task(self) -> Optional[asyncio.Task[None]]:
        """Optional[:class:`asyncio.Task`]: Fetches the internal task or ``None`` if there isn't one running."""
        return self._task if self._task is not None else None

    def is_being_cancelled(self) -> bool:
        """Whether the task is being cancelled."""
        return self._is_being_cancelled

    def failed(self) -> bool:
        return self._has_failed

    def is_running(self) -> bool:
        return not bool(self._task.done()) if self._task else False

    async def _error(self, *args: Any) -> None:
        exception: Exception = args[-1]
        logger.error('Unhandled exception in internal background task {}.', self.coro.__name__, exc_info=exception)

    def before_loop(self, coro: FT) -> FT:
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {coro.__class__.__name__}.')

        self._before_loop = coro
        return coro

    def after_loop(self, coro: FT) -> FT:
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {coro.__class__.__name__}.')

        self._after_loop = coro
        return coro

    def error(self, coro: ET) -> ET:
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {coro.__class__.__name__}.')

        self._error = coro  # type: ignore
        return coro

    def _get_next_sleep_time(self, now: datetime.datetime = None) -> datetime.datetime:
        if self._sleep is not None:
            return self._last_iteration + datetime.timedelta(seconds=self._sleep)

        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        index = self._start_time_relative_to(now)

        if index is None:
            time = self._time[0]
            tomorrow = now.astimezone(time.tzinfo) + datetime.timedelta(days=1)
            date = tomorrow.date()
        else:
            time = self._time[index]
            date = now.astimezone(time.tzinfo).date()

        dt = datetime.datetime.combine(date, time, tzinfo=time.tzinfo)
        return resolve_datetime(dt)

    def _start_time_relative_to(self, now: datetime.datetime) -> Optional[int]:
        # now kwarg should be a datetime.datetime representing the time "now"
        # to calculate the next time index from

        # pre-condition: self._time is set

        # Sole time comparisons are apparently broken, therefore, attach today's date
        # to it in order to make the comparisons make sense.
        # For example, if given a list of times [0, 3, 18]
        # If it's 04:00 today then we know we have to wait until 18:00 today
        # If it's 19:00 today then we know we we have to wait until 00:00 tomorrow
        # Note that timezones need to be taken into consideration for this to work.
        # If the timezone is set to UTC+9 and the now timezone is UTC
        # A conversion needs to be done.
        # i.e. 03:00 UTC+9 -> 18:00 UTC the previous day
        for idx, time in enumerate(self._time):
            # Convert the current time to the target timezone
            # e.g. 18:00 UTC -> 03:00 UTC+9
            # Then compare the time instances to see if they're the same
            start = now.astimezone(time.tzinfo)
            if time >= start.timetz():
                return idx
        else:
            return None

    def _get_time_parameter(
        self,
        time: Union[datetime.time, Sequence[datetime.time]],
        *,
        dt: Type[datetime.time] = datetime.time,
        utc: datetime.timezone = datetime.timezone.utc,
    ) -> List[datetime.time]:
        if isinstance(time, dt):
            inner = time if time.tzinfo is not None else time.replace(tzinfo=utc)
            return [inner]
        if not isinstance(time, Sequence):
            raise TypeError(
                f'Expected datetime.time or a sequence of datetime.time for ``time``, received {type(time)!r} instead.'
            )
        if not time:
            raise ValueError('time parameter must not be an empty sequence.')

        ret: List[datetime.time] = []
        for index, t in enumerate(time):
            if not isinstance(t, dt):
                raise TypeError(
                    f'Expected a sequence of {dt!r} for ``time``, received {type(t).__name__!r} at index {index} instead.'
                )
            ret.append(t if t.tzinfo is not None else t.replace(tzinfo=utc))

        ret = sorted(set(ret))  # de-dupe and sort times
        return ret

    def change_interval(
        self,
        *,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        time: Union[datetime.time, Sequence[datetime.time]] = None,
    ) -> None:
        if time is None:
            seconds = seconds or 0
            minutes = minutes or 0
            hours = hours or 0
            sleep = seconds + (minutes * 60.0) + (hours * 3600.0)
            if sleep < 0:
                raise ValueError('Total number of seconds cannot be less than zero.')

            self._sleep = sleep
            self._seconds = float(seconds)
            self._hours = float(hours)
            self._minutes = float(minutes)
            self._time: List[datetime.time] = None
        else:
            if any((seconds, minutes, hours)):
                raise TypeError('Cannot mix explicit time with relative time')
            self._time = self._get_time_parameter(time)
            self._sleep = self._seconds = self._minutes = self._hours = None

        # Only update the interval if we've ran the body at least once
        if self.is_running() and self._last_iteration is not None:
            self._next_iteration = self._get_next_sleep_time()
            if self._handle and not self._handle.done():
                # the loop is sleeping, recalculate based on new interval
                self._handle.recalculate(self._next_iteration)


def loop(
    *,
    seconds: float = None,
    minutes: float = None,
    hours: float = None,
    time: Union[datetime.time, Sequence[datetime.time]] = None,
    count: Optional[int] = None,
    reconnect: bool = True,
    name: Optional[str] = None,
) -> Callable[[LF], Loop[LF]]:

    def decorator(func: LF) -> Loop[LF]:
        return Loop[LF](
            func,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            count=count,
            time=time,
            reconnect=reconnect,
            name=name,
        )

    return decorator
