"""
Минимальный GUI для запуска прогонов assetto_corsa_gym без консоли.

Запуск:
    python scripts\\gui_launcher.py

Синхронизация: GUI и любой прямой вызов из терминала (в т.ч. от Claude
через Bash) используют общий файл состояния через run_tracker.py -
.run_state.json + .run_logs\\. Кто угодно запускает прогон - оба видят
живой лог и могут его остановить. Смотри run_tracker.py для CLI-запуска
без GUI.

Требует только tkinter (стандартная библиотека, доп. пакеты не нужны).
"""

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tracker  # noqa: E402

SUBMODULE_ROOT = REPO_ROOT / "third_party" / "assetto_corsa_gym"
P309_PYTHON = r"C:\Users\nikit\Miniconda3\envs\p309\python.exe"

DEFAULT_CHECKPOINT = str(
    SUBMODULE_ROOT
    / "results" / "checkpoints" / "data_sets" / "monza" / "bmw_z4_gt3"
    / "20241108_SAC" / "model" / "checkpoints" / "step_05400000"
)

PRESETS = {
    "Тест чекпоинта (--test)": {
        "cwd": SUBMODULE_ROOT,
        "template": [
            P309_PYTHON, "train.py", "--test",
            "--load_path", "{load_path}",
            "AssettoCorsa.track={track}",
            "AssettoCorsa.car={car}",
            "disable_wandb=True",
        ],
        "fields": {
            "load_path": DEFAULT_CHECKPOINT,
            "track": "monza",
            "car": "bmw_z4_gt3",
        },
    },
    "Обучение с нуля (train.py)": {
        "cwd": SUBMODULE_ROOT,
        "template": [
            P309_PYTHON, "train.py",
            "AssettoCorsa.track={track}",
            "AssettoCorsa.car={car}",
            "disable_wandb=True",
        ],
        "fields": {
            "track": "monza",
            "car": "bmw_z4_gt3",
        },
    },
    "Проверка окружения (check_env.py)": {
        "cwd": REPO_ROOT,
        "template": [P309_PYTHON, "scripts/check_env.py"],
        "fields": {},
    },
    "Достать времена кругов (extract_lap_times.py)": {
        "cwd": REPO_ROOT,
        "template": [P309_PYTHON, "scripts/extract_lap_times.py"],
        "fields": {},
    },
    "Диагностика vJoy (vjoy_diag.py)": {
        "cwd": REPO_ROOT,
        "template": [P309_PYTHON, "scripts/vjoy_diag.py"],
        "fields": {},
    },
    "Своя команда": {
        "cwd": SUBMODULE_ROOT,
        "template": None,  # свободный ввод в поле raw
        "fields": {},
    },
}


class LauncherApp:
    POLL_MS = 400

    def __init__(self, root):
        self.root = root
        root.title("AC Gym Launcher")
        root.geometry("900x600")

        self.field_vars = {}
        self.known_log_path = None
        self.log_pos = 0
        self.attached_externally = False

        top = ttk.Frame(root, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Пресет:").pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value=list(PRESETS.keys())[0])
        preset_combo = ttk.Combobox(
            top, textvariable=self.preset_var, values=list(PRESETS.keys()),
            state="readonly", width=40,
        )
        preset_combo.pack(side=tk.LEFT, padx=6)
        preset_combo.bind("<<ComboboxSelected>>", lambda e: self.render_fields())

        self.run_btn = ttk.Button(top, text="Запустить", command=self.start_run)
        self.run_btn.pack(side=tk.LEFT, padx=6)
        self.stop_btn = ttk.Button(top, text="Остановить", command=self.stop_run, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=6)
        self.clear_btn = ttk.Button(top, text="Очистить лог", command=self.clear_log)
        self.clear_btn.pack(side=tk.LEFT, padx=6)

        self.status_var = tk.StringVar(value="Готов")
        ttk.Label(top, textvariable=self.status_var).pack(side=tk.RIGHT)

        self.fields_frame = ttk.Frame(root, padding=(8, 0))
        self.fields_frame.pack(fill=tk.X)

        self.raw_frame = ttk.Frame(root, padding=(8, 4))
        ttk.Label(self.raw_frame, text="Команда (после python.exe окружения p309):").pack(anchor=tk.W)
        self.raw_entry = ttk.Entry(self.raw_frame)
        self.raw_entry.insert(0, "train.py --test AssettoCorsa.track=monza AssettoCorsa.car=bmw_z4_gt3 disable_wandb=True")
        self.raw_entry.pack(fill=tk.X)

        self.log = scrolledtext.ScrolledText(root, state=tk.DISABLED, wrap=tk.WORD, bg="#101010", fg="#d0d0d0")
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.render_fields()
        self.root.after(self.POLL_MS, self.poll_state)

    def render_fields(self):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self.raw_frame.pack_forget()
        self.field_vars = {}

        preset = PRESETS[self.preset_var.get()]
        if preset["template"] is None:
            self.raw_frame.pack(fill=tk.X, after=self.fields_frame)
            return

        for name, default in preset["fields"].items():
            row = ttk.Frame(self.fields_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=name, width=12).pack(side=tk.LEFT)
            var = tk.StringVar(value=default)
            entry = ttk.Entry(row, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.field_vars[name] = var

    def build_command(self):
        preset = PRESETS[self.preset_var.get()]
        if preset["template"] is None:
            return [P309_PYTHON] + self.raw_entry.get().split(), preset["cwd"]
        values = {name: var.get() for name, var in self.field_vars.items()}
        cmd = [part.format(**values) for part in preset["template"]]
        return cmd, preset["cwd"]

    def append_log(self, text):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def clear_log(self):
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

    def start_run(self):
        if run_tracker.read_state() is not None:
            self.append_log("[launcher] Уже есть активный прогон (возможно запущен извне) - сначала останови.\n")
            return
        cmd, cwd = self.build_command()
        try:
            pid, log_path = run_tracker.start_tracked(cmd, cwd)
        except Exception as e:
            self.append_log(f"[launcher] Не удалось запустить: {e}\n")
            return
        self.clear_log()
        self.append_log(f"$ {' '.join(cmd)}\n(cwd: {cwd}, pid: {pid})\n\n")
        self.known_log_path = log_path
        self.log_pos = 0

    def stop_run(self):
        ok = run_tracker.stop_tracked()
        self.append_log("\n[launcher] Остановлено.\n" if ok else "\n[launcher] Нечего останавливать.\n")

    def poll_state(self):
        state = run_tracker.read_state()
        if state is not None and not run_tracker.is_running(state["pid"]):
            # process finished on its own without anyone calling stop
            run_tracker.clear_state()
            state = None

        if state is None:
            if self.known_log_path is not None:
                self.append_log("\n[launcher] Прогон завершён.\n")
            self.known_log_path = None
            self.log_pos = 0
            self.attached_externally = False
            self.status_var.set("Готов")
            self.run_btn.configure(state=tk.NORMAL)
            self.stop_btn.configure(state=tk.DISABLED)
        else:
            log_path = Path(state["log_path"])
            if log_path != self.known_log_path:
                # новый прогон - свой или чужой (запущен извне, например из Bash)
                self.clear_log()
                started_by = state.get("started_by", "?")
                self.append_log(f"[launcher] Подключился к прогону PID={state['pid']} "
                                 f"(started_by={started_by})\n$ {' '.join(state['cmd'])}\n\n")
                self.known_log_path = log_path
                self.log_pos = 0

            if log_path.exists():
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self.log_pos)
                    new_data = f.read()
                    self.log_pos = f.tell()
                if new_data:
                    self.append_log(new_data)

            self.status_var.set(f"Работает (PID {state['pid']})")
            self.run_btn.configure(state=tk.DISABLED)
            self.stop_btn.configure(state=tk.NORMAL)

        self.root.after(self.POLL_MS, self.poll_state)

    def on_close(self):
        # не убиваем прогон при закрытии окна - он может быть общим с Claude/консолью
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
