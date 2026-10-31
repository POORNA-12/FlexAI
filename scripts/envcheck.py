"""Environment self-check - prints interpreter, dependency and import status.

Run with the project interpreter:

    .venv\\Scripts\\python.exe scripts\\envcheck.py

Exit code 0 = every required import resolved.
Used by scripts/verify-fast.ps1 and by hand when a shell's quoting makes -c awkward.
"""

from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path

REQUIRED = ["fastapi", "sqlalchemy", "pydantic", "pydantic_settings", "pymysql", "openpyxl", "pandas", "dotenv"]
DEV = ["pytest", "ruff", "mypy"]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    print(f"python      : {sys.version.split()[0]} ({platform.machine()})")
    print(f"executable  : {sys.executable}")
    print(f"prefix      : {sys.prefix}")
    print(f"project root: {root}")
    print(f"venv in use : {'.venv' in sys.prefix.lower()}")

    missing: list[str] = []
    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "?")
            print(f"  ok   {name:<18} {version}")
        except Exception as exc:  # noqa: BLE001 - report, do not fail the whole run
            print(f"  MISS {name:<18} {type(exc).__name__}: {exc}")
            missing.append(name)

    print("dev tools:")
    for name in DEV:
        try:
            importlib.import_module(name)
            print(f"  ok   {name}")
        except Exception:
            print(f"  warn {name} not installed (advisory)")

    print("")
    if missing:
        print(f"RESULT: FAIL - missing {len(missing)} runtime module(s): {', '.join(missing)}")
        return 1
    print("RESULT: imports OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
