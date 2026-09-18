"""
Общий трекер запущенных прогонов - и для GUI (gui_launcher.py), и для
прямых вызовов из терминала/Claude через Bash. Оба используют один и тот
же файл состояния (.run_state.json) и лог-файлы (.run_logs/), поэтому
видят и могут остановить прогон друг друга, кто бы его ни запустил.

CLI:
    python scripts\\run_tracker.py --cwd <путь> -- <команда...>   # запустить
    python scripts\\run_tracker.py --status                       # статус
    python scripts\\run_tracker.py --stop                         # остановить

Как модуль (используется gui_launcher.py):
    from run_tracker import start_tracked, stop_tracked, read_state, is_running
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / ".run_state.json"
LOGS_DIR = REPO_ROOT / ".run_logs"


def start_tracked(cmd, cwd):
    """Launch a command detached, register it in the shared state file, and
    return immediately (non-blocking). Returns (pid, log_path)."""
    existing = read_state()
    if existing is not None:
        if is_running(existing["pid"]):
            raise RuntimeError(
                "A run is already tracked (.run_state.json). Stop it first (--stop)."
            )
        # stale state left over from a run that finished on its own - clean up
        clear_state()

    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S.%f")[:-3]
    log_path = LOGS_DIR / f"{ts}.log"
    log_file = open(log_path, "w", encoding="utf-8", errors="replace")

    proc = subprocess.Popen(
        cmd, cwd=str(cwd), stdout=log_file, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    state = {
        "pid": proc.pid,
        "cmd": cmd,
        "cwd": str(cwd),
        "log_path": str(log_path),
        "started_at": ts,
        "started_by": os.environ.get("USERNAME", "?"),
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return proc.pid, log_path


def read_state():
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_running(pid):
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True,
    )
    return str(pid) in result.stdout


def clear_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def stop_tracked():
    state = read_state()
    if not state:
        return False
    pid = state["pid"]
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    clear_state()
    return True


def _main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=str(REPO_ROOT))
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.stop:
        ok = stop_tracked()
        print("Stopped." if ok else "No active run.")
        return

    if args.status:
        state = read_state()
        if not state:
            print("No active run.")
        else:
            running = is_running(state["pid"])
            print(json.dumps(state, ensure_ascii=False, indent=2))
            print(f"running: {running}")
        return

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("Need a command after --. Example:")
        print(r'  python scripts\run_tracker.py --cwd third_party\assetto_corsa_gym -- '
              r'C:\Users\nikit\Miniconda3\envs\p309\python.exe train.py --test ...')
        sys.exit(1)

    pid, log_path = start_tracked(cmd, Path(args.cwd))
    print(f"Started. PID={pid}")
    print(f"Log: {log_path}")
    print(r"Status: python scripts\run_tracker.py --status")
    print(r"Stop:   python scripts\run_tracker.py --stop")


if __name__ == "__main__":
    _main()
