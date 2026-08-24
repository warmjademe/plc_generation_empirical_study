"""Dedicated durable background worker for the production deployment."""

from __future__ import annotations

import signal

from . import main


def run() -> None:
    if not main.settings.run_background_jobs:
        raise RuntimeError("PLC worker requires PLC_RUN_BACKGROUND_JOBS=true")

    def stop(_signum: int, _frame: object) -> None:
        main._dispatcher_stop.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    main._dispatcher_stop.clear()
    main._recover_after_process_restart()
    main._dispatcher_loop()


if __name__ == "__main__":
    run()
