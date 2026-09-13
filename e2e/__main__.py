from __future__ import annotations

import asyncio
import sys

from .runner import Runner


def main() -> int:
    return asyncio.run(Runner.from_environment().cli(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
