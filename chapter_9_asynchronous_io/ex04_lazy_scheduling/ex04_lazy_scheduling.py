"""ex04 — when does a task actually run? (Not when you create it.)

The chapter's most counterintuitive claim: inside a `TaskGroup`, the first HTTP request does
not fire when you call `tg.create_task(...)`. A coroutine is a lazy generator — creating it
runs none of its body. A `Task` only advances when the event loop gets a turn, and the loop
only gets a turn when the currently running coroutine hits an `await`. A `for` loop full of
`create_task` calls with no `await` in its body never yields, so every task just sits queued
until the `TaskGroup`'s `__aexit__` awaits them all at once.

We make that visible with two probes: a print at the end of the creation loop, and a print at
the start of each task. If tasks ran on creation, the task prints would interleave with the
loop. They don't — every "creating" line comes first, then the loop-end marker, and only then
do the tasks run. Then we flip on `asyncio.eager_task_factory` and watch the ordering change:
eager tasks run their body immediately up to the first real suspension point.
"""
import asyncio
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir


async def _probe(i, log):
    log.append(("run", i))
    await asyncio.sleep(0)          # the suspension point
    log.append(("resume", i))


async def _build(eager: bool, n: int = 4):
    log = []
    loop = asyncio.get_running_loop()
    if eager:
        loop.set_task_factory(asyncio.eager_task_factory)
    async with asyncio.TaskGroup() as tg:
        for i in range(n):
            log.append(("create", i))
            tg.create_task(_probe(i, log))
        log.append(("loop-end", None))
    return log


def run(eager: bool):
    return asyncio.run(_build(eager))


def first_run_index(log):
    """Position in the log where the first task body ('run') executes."""
    for pos, (kind, _) in enumerate(log):
        if kind == "run":
            return pos
    return -1


def _render(log):
    for kind, i in log:
        label = f"{kind} {i}" if i is not None else kind
        print(f"    {label}")


def main():
    lazy = run(eager=False)
    eager = run(eager=True)
    loop_end_lazy = next(p for p, (k, _) in enumerate(lazy) if k == "loop-end")
    loop_end_eager = next(p for p, (k, _) in enumerate(eager) if k == "loop-end")

    print("default (lazy) tasks — bodies run AFTER the creation loop:")
    _render(lazy)
    print(f"  first task body at position {first_run_index(lazy)}; loop-end at {loop_end_lazy}")

    print("\neager_task_factory — bodies run DURING creation, up to first await:")
    _render(eager)
    print(f"  first task body at position {first_run_index(eager)}; loop-end at {loop_end_eager}")

    assert first_run_index(lazy) > loop_end_lazy, "lazy: tasks should run after loop-end"
    assert first_run_index(eager) < loop_end_eager, "eager: tasks should run before loop-end"
    print("\nVERIFIED: lazy tasks start after the loop; eager tasks start during it.")


if __name__ == "__main__":
    main()
