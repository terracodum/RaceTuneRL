# Установка плагина assetto_corsa_gym в Assetto Corsa

Путь к AC на этой машине: `X:\SteamLibrarySSD\steamapps\common\assettocorsa`
(подставлен ниже везде вместо плейсхолдера). Источник шагов —
`third_party/assetto_corsa_gym/INSTALL.md` (Windows-инструкция апстрима).
Делает человек руками, скрипты этого репо AC не трогают.

## 1. vJoy (виртуальный джойстик)

Нужен, чтобы среда могла слать команды в игру (`INSTALL.md:8-11`).

1. Скачать и поставить vJoy: https://sourceforge.net/projects/vjoystick/

## 2. Копирование плагина

Источник в репо: `third_party/assetto_corsa_gym/assetto_corsa_gym/AssettoCorsaPlugin/plugins/sensors_par`
(`INSTALL.md:15-28`).

1. Скопировать папку `sensors_par` целиком в:
   ```
   X:\SteamLibrarySSD\steamapps\common\assettocorsa\apps\python\
   ```
   Итоговый путь должен быть:
   ```
   X:\SteamLibrarySSD\steamapps\common\assettocorsa\apps\python\sensors_par
   ```

## 3. Конфиги vJoy/WASD и DLL

Источник: `third_party/assetto_corsa_gym/assetto_corsa_gym/AssettoCorsaPlugin/windows-libs`
(`INSTALL.md:32-52`).

1. Скопировать `Vjoy.ini` и `WASD.ini` в:
   ```
   %USERPROFILE%\Documents\Assetto Corsa\cfg\controllers\savedsetups
   ```
2. Скопировать папки `DLLs` и `Lib` из `windows-libs` в:
   ```
   X:\SteamLibrarySSD\steamapps\common\assettocorsa\system\x64
   ```
   (это библиотека Python-сокетов, нужна плагину внутри встроенного
   Python 3.3 игры).

## 4. Custom Shaders Patch

Нужен для сброса машины (`ac.ext_resetCar()`, вызывается плагином при reset)
— `INSTALL.md:56-65`.

1. Поставить Content Manager: https://acstuff.ru/app/
2. В Content Manager → Settings → Custom Shaders Patch → Install.

## 5. Включить плагин в игре

`INSTALL.md:71-74`.

1. Запустить Assetto Corsa.
2. Options → General → UI Modules → включить `sensor_par`.
   (Папка называется `sensors_par`, но в списке модулей AC может показывать
   имя из `ui.json` плагина — ищи "sensor_par"/"sensors_par" в списке; если
   не находится, проверить, что папка лежит именно в `apps\python\`, а не
   на уровень выше/ниже.)

## 6. Настройка управления

`INSTALL.md:76-79`.

1. Options → Controls.
2. Убедиться, что доступны и vJoy, и WASD.
3. Выбрать vJoy как активный input-девайс.

## 7. Видео/частота кадров

`INSTALL.md:81-83`. Это жёсткое требование протокола — плагин ассертит
`sampling_freq=50` при старте (`.../sensors_par/config.py:5,48-51`).

1. Options → Video → Display → Framerate Limit → **50 FPS**.

## 8. Режим сессии

`INSTALL.md:85-86`.

1. Challenge → Hotlap.

## 9. Настройки ассистов (Driving Assists)

`INSTALL.md:88-108`. Важно: коробка передач в этом форке не управляется
RL-агентом вообще (см. `docs/acgym_audit.md`, п.4) — штатный сетап форка
рассчитан на автомат:

| Настройка | Значение |
|---|---|
| Automatic Gearbox | ON |
| Ideal Racing Line | как удобно |
| Automatic Clutch | Enabled |
| Automatic Throttle Blip | Disabled |
| Traction Control | OFF |
| Stability Control | OFF |
| Mechanical Damage | OFF |
| Tyre Blankets | ON |
| ABS | OFF |
| Fuel Consumption | OFF |
| Tyre Wear | OFF |
| Slipstream Effect | 1x |
| Time of Day | 10:00 |
| Weather | Mid Clear |
| Ambient Temperature | 26°C |
| Time Multiplier | 1x |
| Track Surface | Optimum |
| Penalties | ON |

Если по проекту решится делать ручную коробку — эти настройки (Automatic
Gearbox/Clutch) и код придётся менять отдельно, это не входит в данную
инструкцию (см. открытые вопросы в `docs/acgym_audit.md`).

## Проверка, что плагин поднялся

1. Запустить AC, зайти в Hotlap-сессию на любой уже настроенной трассе/машине
   (пока не Magione/RSR — их конфигов в форке ещё нет, см. `docs/acgym_audit.md`, п.10-11).
2. В консоли AC/логах плагина должно появиться сообщение
   `[EGO SERV] Start ego server socket on: ...` (`.../sensors_par/ego_server.py:117`).
3. Из окружения `p309` (после `conda env create -f environment.yml` и
   `python scripts/check_env.py`) можно проверить сокет-соединение через
   `third_party/assetto_corsa_gym/test_client.ipynb` — не входит в эту
   инструкцию, отдельный шаг после того как плагин виден в игре.
