#!/usr/bin/env python
"""
Development Server Manager - Start/Stop/Restart mit einem Befehl.

Usage:
    python dev.py start    # Backend starten
    python dev.py stop     # Backend stoppen
    python dev.py restart  # Backend neustarten
    python dev.py status   # Status prüfen
    python dev.py test     # Tests ausführen
"""

import subprocess
import sys
import os
import signal
from pathlib import Path

PID_FILE = Path(__file__).parent / ".dev_server.pid"
BACKEND_DIR = Path(__file__).parent


def get_pid():
    """Liest die PID aus der Datei."""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, FileNotFoundError):
            return None
    return None


def is_running(pid):
    """Prüft ob Prozess läuft."""
    if pid is None:
        return False
    try:
        if os.name == 'nt':
            # Windows: tasklist prüfen
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except OSError:
        return False


def is_port_in_use(port=8000):
    """Prüft ob Port bereits belegt ist."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def start():
    """Startet den Development Server."""
    pid = get_pid()
    if is_running(pid):
        print(f"[dev] Server läuft bereits (PID {pid})")
        return

    print("[dev] Starte Backend auf http://localhost:8000 ...")

    # Start uvicorn in background
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )

    PID_FILE.write_text(str(process.pid))
    print(f"[dev] Server gestartet (PID {process.pid})")
    print("[dev] Logs: python dev.py logs")


def stop():
    """Stoppt den Development Server."""
    pid = get_pid()
    if not is_running(pid):
        print("[dev] Server läuft nicht")
        PID_FILE.unlink(missing_ok=True)
        return

    print(f"[dev] Stoppe Server (PID {pid}) ...")

    try:
        if os.name == 'nt':
            # Windows: taskkill
            subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"],
                         capture_output=True)
        else:
            # Unix: SIGTERM
            os.kill(pid, signal.SIGTERM)
    except Exception as e:
        print(f"[dev] Fehler beim Stoppen: {e}")

    PID_FILE.unlink(missing_ok=True)
    print("[dev] Server gestoppt")


def restart():
    """Neustart des Servers."""
    stop()
    import time
    time.sleep(1)
    start()


def status():
    """Zeigt den Server-Status."""
    pid = get_pid()
    port_active = is_port_in_use(8000)

    if is_running(pid) or port_active:
        print(f"[dev] Server läuft (PID {pid or '?'}, Port 8000 aktiv)")
        print("[dev] URL: http://localhost:8000")
        print("[dev] Docs: http://localhost:8000/docs")
    else:
        print("[dev] Server läuft nicht")
        PID_FILE.unlink(missing_ok=True)


def test():
    """Führt die Tests aus."""
    print("[dev] Führe Tests aus...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=BACKEND_DIR
    )
    sys.exit(result.returncode)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    commands = {
        "start": start,
        "stop": stop,
        "restart": restart,
        "status": status,
        "test": test,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"[dev] Unbekannter Befehl: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
