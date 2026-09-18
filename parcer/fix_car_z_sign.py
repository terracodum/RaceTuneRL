"""
Разовая коррекция car_z для CSV, записанных ДО фикса знака в lap_recorder.py
(коммит 3e3359d, "fix z axis"). Сырой CSV не трогается - читает его и
пишет отдельный производный файл с уже инвертированным car_z, в том же
соглашении о знаке, что и записи, сделанные рекордером после фикса
(parcer/lap_recorder.py:205: "car_z": -round(gfx.carCoordinates[2], 2)).

Запуск:
    python parcer/fix_car_z_sign.py data/lap_2026-05-27_13-23-37.csv

Без второго аргумента пишет рядом с суффиксом .car_z_fixed.csv.
"""

import csv
import sys
from pathlib import Path


def fix(input_path: Path, output_path: Path):
    with open(input_path, newline="") as fin, open(output_path, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            row["car_z"] = round(-float(row["car_z"]), 2)
            writer.writerow(row)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parcer/fix_car_z_sign.py <input.csv> [output.csv]")
        sys.exit(1)
    input_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.with_suffix(".car_z_fixed.csv")
    fix(input_path, output_path)
    print(f"Written: {output_path}")
