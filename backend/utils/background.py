# utils/background.py — fire-and-forget tasks that must not block a request.

import asyncio

_tasks: set[asyncio.Task] = set()


def spawn(coro) -> None:
    """Run ``coro`` in the background. A reference is kept until it finishes:
    the event loop only holds weak references, so an unreferenced task can be
    garbage-collected mid-run."""
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
