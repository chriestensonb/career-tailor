import asyncio
import itertools
import sys
from contextlib import asynccontextmanager


@asynccontextmanager
async def spinner(message: str = "Working"):
    """Async context manager that shows a terminal spinner while awaiting."""
    frames = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])

    async def _spin() -> None:
        try:
            while True:
                frame = next(frames)
                print(f"\r{message} {frame}", end="", flush=True, file=sys.stderr)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(_spin())
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        print(f"\r{' ' * (len(message) + 3)}\r", end="", flush=True, file=sys.stderr)
