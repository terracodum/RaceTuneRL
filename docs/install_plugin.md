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

1. **Скопировать** (не переместить/вырезать!) папку `sensors_par` целиком в:
   ```
   X:\SteamLibrarySSD\steamapps\common\assettocorsa\apps\python\
   ```
   Итоговый путь должен быть:
   ```
   X:\SteamLibrarySSD\steamapps\common\assettocorsa\apps\python\sensors_par
   ```
   Важно: если вырезать (Cut) вместо копировать — папка пропадёт из
   `third_party/assetto_corsa_gym/assetto_corsa_gym/AssettoCorsaPlugin/plugins/sensors_par`,
   а она там ТОЖЕ нужна (`ac_client.py:10` импортирует `car_control.Controls`
   оттуда же, для локального управления через vJoy на стороне питон-клиента).
   Если случайно вырезал — восстановить: `cd third_party\assetto_corsa_gym`
   → `git checkout -- assetto_corsa_gym/AssettoCorsaPlugin/plugins/sensors_par`.

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

Нужен не только для сброса машины (`ac.ext_resetCar()`) — плагин на
**каждый кадр** дёргает `ac.ext_isAltPressed()`
(`.../sensors_par/sensors_par.py:255`), это тоже CSP-расширение API.
Без активного CSP это падает с `[PY ERROR] 'module' object has no
attribute 'ext_isAltPressed'` на каждый кадр (видно в
`Documents\Assetto Corsa\logs\log.txt`) — краш происходит ДО строки,
которая шлёт телеметрию клиенту (`ego_server.tick()`,
`sensors_par.py:280`), поэтому симптом такой: питон-клиент подключается
(handshake проходит раньше), но дальше зависает намертво без единой
ошибки на своей стороне — сброс/шаги никогда не завершаются.

1. Поставить Content Manager: https://acstuff.ru/app/
2. В Content Manager → Settings → Custom Shaders Patch → Install (проверить
   что статус "Active", не просто кнопка Install).
3. **Игру запускать через Content Manager**, не напрямую через Steam/ярлык —
   иначе патч может быть не подключён для сессии.
4. На экране запуска (Content Manager → Hotlap/Race, вкладка выбора
   трассы/машины) включить галочку **"Use extended physics"** — без неё
   `ac.ext_*` функции недоступны даже при установленном и активном CSP.
5. Если проблема осталась после этого — попробовать в Custom Shaders Patch
   → "Reinstall current version" и полностью перезапустить AC.

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

1. Options → Controls → **wheel/custom** (не xbox/gamepad, не keyboard).
2. В списке **Configuration Presets** должен быть пресет `Vjoy` (мы
   копировали `Vjoy.ini` в шаге 3) — выбрать его и нажать **apply preset**.
   Если пресета нет в списке — проверить, что `Vjoy.ini` реально лежит в
   `savedsetups` (шаг 3), и **полностью перезапустить AC** (список
   пресетов сканируется при старте игры, не обновляется на лету).
3. После применения пресета в Main Controls должно быть: Steering → Axis 1
   (vJoy Device), Throttle → Axis 2, Brakes → Axis 3.
4. vJoy — виртуальное устройство, руками (без запущенного питон-клиента)
   его оси не подвигать, чтобы проверить биндинг — это нормально, не
   баг настройки.

## 7. Видео/частота кадров

`INSTALL.md:81-83`. Это жёсткое требование протокола — плагин ассертит
`sampling_freq=50` при старте (`.../sensors_par/config.py:5,48-51`), и
**шлёт телеметрию по счётчику кадров, а не по времени**
(`ego_server.py:205`: раз в `sampling_freq // ego_sampling_freq` вызовов
`acUpdate()`). Если реальный FPS выше 50 (например, без лимита — 180),
телеметрия улетает клиенту значительно чаще расчётных 25 Гц, вся
синхронизация по времени ломается: на практике это выглядит как
аномальный разброс `dt` (вплоть до отрицательных значений) и заметные
потери пакетов (десятки процентов от шагов) в логе питон-клиента.

1. Options → Video → Display → Framerate Limit → **50 FPS**.
2. **Обязательно проверить фактический FPS** после этого (по счётчику в
   игре/CSP), не только что настройка стоит — лимит иногда не применяется
   молча (наблюдалось: лимит стоял на 50, а реально было 180).

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

Если запускаешь сессию через **Content Manager** (см. шаг 4) — на экране
Quick Drive/Hotlap отдельные тумблеры ассистов не всегда доступны, только
именованные пресеты сложности в выпадающем списке (Gamer/Intermediate/Pro).
**Gamer** обычно уже включает Automatic Gearbox/Clutch по умолчанию,
**Pro** — нет (расчитан на полностью ручное управление). Если нужен точный
контроль по таблице выше — этот список настроек доступен в самой игре
(не в Content Manager) на экране подготовки к заезду (Challenge → Hotlap →
блок Realism/Assists → вкладка Custom).

## Проверка, что плагин поднялся

1. Запустить AC, зайти в Hotlap-сессию на любой уже настроенной трассе/машине
   (пока не Magione/RSR — их конфигов в форке ещё нет, см. `docs/acgym_audit.md`, п.10-11).
2. В консоли AC/логах плагина должно появиться сообщение
   `[EGO SERV] Start ego server socket on: ...` (`.../sensors_par/ego_server.py:117`).
3. Из окружения `p309` (после `conda env create -f environment.yml` и
   `python scripts/check_env.py`) можно проверить сокет-соединение через
   `third_party/assetto_corsa_gym/test_client.ipynb` — не входит в эту
   инструкцию, отдельный шаг после того как плагин виден в игре.
