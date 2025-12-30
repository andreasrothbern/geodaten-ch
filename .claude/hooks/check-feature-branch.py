#!/usr/bin/env python3
"""
Prueft ob User auf main/master ist und erinnert an Feature-Branch.
Laeuft bei SessionStart.
"""
import json
import subprocess
import sys

def get_current_branch():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return None

def main():
    current_branch = get_current_branch()

    if current_branch in ("main", "master"):
        warning = f"""
WARNUNG: Du bist auf dem '{current_branch}' Branch!

Vor der Implementierung neuer Features, erstelle einen Feature-Branch:
  git checkout -b feature/dein-feature-name

Beispiele:
  git checkout -b feature/svg-export
  git checkout -b fix/height-calculation
  git checkout -b chore/update-deps

Dies schuetzt main vor versehentlichen Aenderungen.
"""

        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": warning.strip()
            }
        }
        print(json.dumps(output))

    sys.exit(0)

if __name__ == "__main__":
    main()
