"""
Достаёт времена кругов из лога прогона train.py --test.

train.py без явного work_dir/config.work_dir пишет в
third_party/assetto_corsa_gym/outputs/<timestamp>/ (train.py:49-56).
Там eval_summary.csv - один ряд с результатом agent.evaluate()
(discor/agent.py:250-269), посчитанный в AssettoCorsaEnv.end_of_episode_stats
(ac_env.py:788-856): колонки LapNo_0, LapNo_1, ... (сек, по кругам за
эпизод), ep_bestLapTime (сек, лучший завершённый круг, исключая 0),
BestLap (сек, счётчик самой AC).

Запуск:
    python scripts/extract_lap_times.py                  # берёт последний outputs/*
    python scripts/extract_lap_times.py <path_to_work_dir>
"""

import sys
import glob
import os
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "third_party" / "assetto_corsa_gym" / "outputs"


def find_latest_work_dir():
    candidates = sorted(glob.glob(str(OUTPUTS_ROOT / "*")), key=os.path.getmtime)
    if not candidates:
        raise FileNotFoundError(f"No run directories found under {OUTPUTS_ROOT}")
    return Path(candidates[-1])


def load_lap_times(work_dir: Path):
    eval_summary_path = work_dir / "eval_summary.csv"
    episodes_stats_path = work_dir / "episodes_stats.csv"

    if eval_summary_path.exists():
        source_path = eval_summary_path
    elif episodes_stats_path.exists():
        source_path = episodes_stats_path
    else:
        raise FileNotFoundError(
            f"Neither eval_summary.csv nor episodes_stats.csv found in {work_dir}"
        )

    df = pd.read_csv(source_path)
    return df, source_path


def main():
    if len(sys.argv) > 1:
        work_dir = Path(sys.argv[1])
    else:
        work_dir = find_latest_work_dir()

    print(f"work_dir: {work_dir}")
    df, source_path = load_lap_times(work_dir)
    print(f"source: {source_path}")
    print()

    lap_cols = [c for c in df.columns if c.startswith("LapNo_")]

    for _, row in df.iterrows():
        print(f"ep_count: {row.get('ep_count', 'n/a')}")
        for c in lap_cols:
            val = row[c]
            print(f"  {c}: {val:.3f} s" if val > 0 else f"  {c}: {val} (incomplete/out lap)")
        if "ep_bestLapTime" in row:
            print(f"  ep_bestLapTime: {row['ep_bestLapTime']:.3f} s")
        if "BestLap" in row:
            print(f"  BestLap (AC counter): {row['BestLap']:.3f} s")
        print()

    if "ep_bestLapTime" in df.columns:
        best = df["ep_bestLapTime"].max()
        print(f"Best lap across all rows: {best:.3f} s (upstream claim for monza/bmw_z4_gt3: ~112.1 s)")


if __name__ == "__main__":
    main()
