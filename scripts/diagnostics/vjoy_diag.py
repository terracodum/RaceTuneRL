"""
Диагностика vJoy напрямую, без AC/train.py.

Пробует захватить устройство (AcquireVJD) и записать в ось throttle
(wAxisY) несколько раз с задержкой, чтобы можно было увидеть в
"Configure vJoy" (или в Options -> Controls -> Main Controls в AC),
шевелится ли ось.

Запуск:
    python scripts\\vjoy_diag.py
"""
import ctypes
import struct
import time

DLL_PATH = r"C:\Program Files\vJoy\x64\vJoyInterface.dll"
DEVICE = 1
SCALE = 16384

print(f"Loading {DLL_PATH} ...")
dll = ctypes.CDLL(DLL_PATH)

acquired = dll.AcquireVJD(DEVICE)
print(f"AcquireVJD(device={DEVICE}) -> {acquired} ({'OK' if acquired else 'FAILED'})")

if not acquired:
    print("Устройство не захвачено. Возможные причины:")
    print("  - оно уже 'занято' зависшим процессом с прошлого запуска")
    print("  - vJoy driver не запущен / не enable-нут")
    print("Попробуй: закрыть все python-процессы, открыть 'Configure vJoy',")
    print("снять и заново поставить галочку 'Enable vJoy', попробовать снова.")
else:
    print("Двигаю throttle (Axis Y) туда-сюда 5 раз, по 1 сек. Смотри на ось")
    print("в Configure vJoy или в AC Options->Controls->Main Controls (Throttle).")
    joyPosFormat = "BlllllllllllllllllllIIII"
    for i in range(5):
        val = SCALE if i % 2 == 0 else 0
        pos = struct.pack(joyPosFormat, DEVICE, 0, 0, 0, 0, val, 0,
                           0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        ok = dll.UpdateVJD(DEVICE, pos)
        print(f"  step {i}: UpdateVJD -> {ok} ({'OK' if ok else 'FAILED'}), value={val}")
        time.sleep(1)

    dll.RelinquishVJD(DEVICE)
    print("Done, released device.")
