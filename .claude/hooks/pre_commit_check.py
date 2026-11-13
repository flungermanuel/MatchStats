"""Hook: blockiert `git commit`, solange pytest oder ruff nicht grün sind.

Claude Code ruft das Skript vor jedem Bash-Befehl auf und übergibt den Befehl als JSON auf stdin.
Exit-Code 2 blockiert den Befehl; die Meldung auf stderr geht an Claude.
"""

import json
import re
import subprocess
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = str(data.get("tool_input", {}).get("command", ""))
    if not re.search(r"\bgit\s+(?:-\S+\s+)*commit\b", command):
        return 0

    checks = [
        ("pytest", [sys.executable, "-m", "pytest", "-q"]),
        ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
    ]
    for name, cmd in checks:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Commit blockiert: {name} ist rot.\n", file=sys.stderr)
            print((result.stdout + result.stderr)[-2000:], file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
