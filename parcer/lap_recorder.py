"""
lap_recorder.py
---------------
Reads Assetto Corsa Shared Memory while you drive and saves telemetry to CSV.
Run this script OUTSIDE the game, in a separate terminal.

Usage:
    python parser/lap_recorder.py

Output:
    data/lap_YYYY-MM-DD_HH-MM-SS.csv
"""

import mmap
import ctypes
import struct
import csv
import time
import os
from datetime import datetime


# ── Shared Memory structs (AC physics page) ──────────────────────────────────

class ACPhysics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId",              ctypes.c_int),
        ("gas",                   ctypes.c_float),
        ("brake",                 ctypes.c_float),
        ("fuel",                  ctypes.c_float),
        ("gear",                  ctypes.c_int),
        ("rpms",                  ctypes.c_int),
        ("steerAngle",            ctypes.c_float),
        ("speedKmh",              ctypes.c_float),
        ("velocity",              ctypes.c_float * 3),
        ("accG",                  ctypes.c_float * 3),   # [lateral, vertical, longitudinal]
        ("wheelSlip",             ctypes.c_float * 4),
        ("wheelLoad",             ctypes.c_float * 4),
        ("wheelsPressure",        ctypes.c_float * 4),
        ("wheelAngularSpeed",     ctypes.c_float * 4),
        ("tyreWear",              ctypes.c_float * 4),
        ("tyreDirtyLevel",        ctypes.c_float * 4),
        ("tyreCoreTemperature",   ctypes.c_float * 4),
        ("camberRAD",             ctypes.c_float * 4),
        ("suspensionTravel",      ctypes.c_float * 4),
        ("drs",                   ctypes.c_float),
        ("tc",                    ctypes.c_float),
        ("heading",               ctypes.c_float),
        ("pitch",                 ctypes.c_float),
        ("roll",                  ctypes.c_float),
        ("cgHeight",              ctypes.c_float),
        ("carDamage",             ctypes.c_float * 5),
        ("numberOfTyresOut",      ctypes.c_int),
        ("pitLimiterOn",          ctypes.c_int),
        ("abs",                   ctypes.c_float),
    ]


class ACGraphics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId",              ctypes.c_int),
        ("status",                ctypes.c_int),        # AC_OFF / AC_LIVE / AC_PAUSE
        ("session",               ctypes.c_int),
        ("currentTime",           ctypes.c_wchar * 15),
        ("lastTime",              ctypes.c_wchar * 15),
        ("bestTime",              ctypes.c_wchar * 15),
        ("split",                 ctypes.c_wchar * 15),
        ("completedLaps",         ctypes.c_int),
        ("position",              ctypes.c_int),
        ("iCurrentTime",          ctypes.c_int),        # ms
        ("iLastTime",             ctypes.c_int),        # ms
        ("iBestTime",             ctypes.c_int),        # ms
        ("sessionTimeLeft",       ctypes.c_float),
        ("distanceTraveled",      ctypes.c_float),
        ("isInPit",               ctypes.c_int),
        ("currentSectorIndex",    ctypes.c_int),
        ("lastSectorTime",        ctypes.c_int),
        ("numberOfLaps",          ctypes.c_int),
        ("tyreCompound",          ctypes.c_wchar * 33),
        ("replayTimeMultiplier",  ctypes.c_float),
        ("normalizedCarPosition", ctypes.c_float),      # 0..1 along track
        ("carCoordinates",        ctypes.c_float * 3),
        ("penaltyTime",           ctypes.c_float),
        ("flag",                  ctypes.c_int),
        ("idealLineOn",           ctypes.c_int),
        ("isInPitLane",           ctypes.c_int),
        ("surfaceGrip",           ctypes.c_float),
        ("mandatoryPitDone",      ctypes.c_int),
        ("windSpeed",             ctypes.c_float),
        ("windDirection",         ctypes.c_float),
    ]


AC_LIVE  = 2
SAMPLE_HZ = 25          # записываем 25 раз в секунду
SLEEP    = 1.0 / SAMPLE_HZ


# ── Shared Memory helpers ─────────────────────────────────────────────────────

def open_shm(name: str, size: int) -> mmap.mmap:
    return mmap.mmap(-1, size, tagname=name, access=mmap.ACCESS_READ)


def read_struct(shm: mmap.mmap, cls):
    shm.seek(0)
    buf = shm.read(ctypes.sizeof(cls))
    return cls.from_buffer_copy(buf)


# ── CSV helpers ───────────────────────────────────────────────────────────────

FIELDS = [
    "timestamp_ms",
    "lap",
    "lap_time_ms",
    "normalized_pos",      # 0..1 вдоль трассы
    "speed_kmh",
    "throttle",
    "brake",
    "steer",
    "gear",
    "rpms",
    "g_lat",               # боковая перегрузка
    "g_lon",               # продольная перегрузка
    "wheel_slip_fl", "wheel_slip_fr", "wheel_slip_rl", "wheel_slip_rr",
    "tyres_out",
    "penalty_time",
    "car_x", "car_y", "car_z",
]


def make_output_path() -> str:
    os.makedirs("data", exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join("data", f"lap_{ts}.csv")


# ── Main loop ─────────────────────────────────────────────────────────────────

def record():
    print("Подключаюсь к Assetto Corsa Shared Memory...")
    print("Запусти AC и начни сессию. Для остановки — Ctrl+C\n")

    try:
        phys_shm = open_shm("Local\\acpmf_physics",  ctypes.sizeof(ACPhysics))
        gfx_shm  = open_shm("Local\\acpmf_graphics", ctypes.sizeof(ACGraphics))
    except Exception as e:
        print(f"Ошибка: не удалось открыть Shared Memory — {e}")
        print("Убедись что AC запущен и сессия активна.")
        return

    out_path = make_output_path()
    print(f"Пишем данные в: {out_path}\n")

    prev_lap      = -1
    prev_packet   = -1
    row_count     = 0
    start_ms      = int(time.time() * 1000)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        try:
            while True:
                phys = read_struct(phys_shm, ACPhysics)
                gfx  = read_struct(gfx_shm,  ACGraphics)

                # Пишем только когда AC живой и packetId обновился
                if gfx.status != AC_LIVE or phys.packetId == prev_packet:
                    time.sleep(SLEEP)
                    continue

                prev_packet = phys.packetId

                # Новый круг — сообщаем в консоль
                if gfx.completedLaps != prev_lap and prev_lap != -1:
                    print(f"  Круг {gfx.completedLaps} завершён — {gfx.iLastTime} ms")
                prev_lap = gfx.completedLaps

                row = {
                    "timestamp_ms":    int(time.time() * 1000) - start_ms,
                    "lap":             gfx.completedLaps,
                    "lap_time_ms":     gfx.iCurrentTime,
                    "normalized_pos":  round(gfx.normalizedCarPosition, 4),
                    "speed_kmh":       round(phys.speedKmh, 2),
                    "throttle":        round(phys.gas,   3),
                    "brake":           round(phys.brake, 3),
                    "steer":           round(phys.steerAngle, 4),
                    "gear":            phys.gear - 1,
                    "rpms":            phys.rpms,
                    "g_lat":           round(phys.accG[0], 4),
                    "g_lon":           round(phys.accG[2], 4),
                    "wheel_slip_fl":   round(phys.wheelSlip[0], 4),
                    "wheel_slip_fr":   round(phys.wheelSlip[1], 4),
                    "wheel_slip_rl":   round(phys.wheelSlip[2], 4),
                    "wheel_slip_rr":   round(phys.wheelSlip[3], 4),
                    "tyres_out":       phys.numberOfTyresOut,
                    "penalty_time":    round(gfx.penaltyTime, 3),
                    "car_x":           round(gfx.carCoordinates[0], 2),
                    "car_y":           round(gfx.carCoordinates[1], 2),
                    "car_z":           -round(gfx.carCoordinates[2], 2),
                }

                writer.writerow(row)
                row_count += 1

                if row_count % 250 == 0:  # каждые ~10 сек
                    print(f"  [{row_count} сэмплов] lap={gfx.completedLaps} "
                          f"speed={phys.speedKmh:.1f} km/h "
                          f"tyres_out={phys.numberOfTyresOut}")

                time.sleep(SLEEP)

        except KeyboardInterrupt:
            print(f"\nОстановлено. Записано {row_count} сэмплов → {out_path}")

    phys_shm.close()
    gfx_shm.close()


if __name__ == "__main__":
    record()