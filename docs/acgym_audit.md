# Аудит форка assetto_corsa_gym (third_party/assetto_corsa_gym)

Все ссылки — на файлы внутри `third_party/assetto_corsa_gym/`, если не сказано иное.
Код не менялся, только чтение.

## 1. Связь с игрой

Три канала, всё через сокеты, без общей shared memory для физики:

- **UDP** — основной канал состояние↔управление. Сервер в плагине:
  `assetto_corsa_gym/AssettoCorsaPlugin/plugins/sensors_par/ego_server.py:113-115`
  (`socket.AF_INET, SOCK_DGRAM`, bind на `ego_server_port`). Клиент (Python-среда,
  вне игры) — `assetto_corsa_gym/AssettoCorsaEnv/ac_client.py:97-114` (`setup_connection`,
  тоже `SOCK_DGRAM`).
- **TCP** — служебные команды: `simulation_management` (reset/get_track_info/
  get_static_info/get_config), порт 2347 — сервер в
  `.../sensors_par/sensors_par.py:111-161`, клиент в `ac_client.py:19-56`.
  Отдельный TCP-сервер для оппонентов (`sensors_par.py:80-109`, порт 2346) —
  в текущем конфиге не используется (0 оппонентов).
- **Именованные Windows-события/shared memory (win32event + dual_buffer)** —
  только для захвата экрана (скриншоты), не для физики: `ac_client.py:9-13,79-82`,
  `ego_server.py:16-20,86-89,195-201`. Отключено по умолчанию
  (`config.yml:80` `screen_capture_enable: False`).
- Сама телеметрия внутри плагина читается не через сырую AC Shared Memory (как
  в `parcer/lap_recorder.py` у нас), а через API самой игры: `ac.getCarState(...)`,
  `acsys.CS.*` — `.../sensors_par/structures.py:36-160`. Несколько полей всё же
  берутся из `sim_info`/`info.graphics`/`info.physics` (обёртка над AC SHM внутри
  плагина) — `structures.py:34-35,61-63,80-82`.

**Что ставится в AC:**
- vJoy (виртуальный джойстик, драйвер) — `INSTALL.md:8-11`; используется в
  `.../sensors_par/car_control.py:1-26` для отправки команд в игру.
- Плагин `sensors_par` копируется в `apps\python\` AC — `INSTALL.md:15-28`.
- Custom Shaders Patch — нужен для `ac.ext_resetCar()` (сброс машины) —
  `INSTALL.md:56-65`, вызов в `.../sensors_par/sensors_par.py:75-78`.
- Конфиги `Vjoy.ini`/`WASD.ini` в `Documents\Assetto Corsa\cfg\controllers\savedsetups`
  — `INSTALL.md:38-47`.

## 2. Частота step

- Тик самого плагина (частота FPS игры) — `sampling_freq=50` Гц,
  `.../sensors_par/config.py:5`, с ассертом на соответствие
  `vjoy_executed_by_server` (`config.py:48-51`).
- Даунсемпл до частоты, с которой плагин реально шлёт телеметрию клиенту —
  `ego_sampling_freq=25` Гц, `config.py:9`; тик отправки — раз в
  `sampling_freq // ego_sampling_freq` игровых тиков,
  `ego_server.py:187,204-205`. В `config.yml:51` то же самое: `ego_sampling_freq: 25`,
  сверяется в рантайме с плагином — `assetto_corsa_gym/AssettoCorsaEnv/ac_env.py:659`.
  Это и есть ответ на открытый вопрос в нашем CLAUDE.md "25 или 40 Гц" — в форке
  зашито и заассертено именно 25 Гц.
- **Шаг синхронный/блокирующий**: `AssettoCorsaEnv.step()` → `client.step_sim()` →
  `get_servers_input()` крутит цикл `recvfrom` с таймаутом 2с, пока не придёт
  новый UDP-пакет от игры (`ac_client.py:99,122-146,176-182`). Т.е. `step()`
  реально ждёт следующий тик игры в реальном времени — не turn-based и не fast-forward.
- **Во время градиентного шага игра не останавливается.** В цикле обучения
  (`algorithm/discor/discor/agent.py:154-164`) действие отправляется в игру
  сразу (`self._env.set_actions(action)`, неблокирующе), затем выполняется
  `self.update_model()` (шаг SGD), и только потом идёт блокирующий
  `self._env.step(action=None)` за следующим наблюдением. Игра продолжает жить
  в реальном времени параллельно с обновлением сети; если обновление медленнее
  такта игры, агент просто ждёт дольше на следующем `step()` (эффективно
  "теряет" реальное время, а не кадры/тики — тики продолжают идти).

## 3. Вектор наблюдения

Собирается в `ac_env.py:702-761` (`get_obs`), размерность считается в
`__init__` (`ac_env.py:337-355`). По умолчанию (`config.yml`:
`enable_sensors=True`, `add_previous_obs_to_state=True`, `use_target_speed=False`,
`enable_task_id_in_obs=False`):

| компонент | размер | источник |
|---|---|---|
| базовые каналы (`obs_enabled_channels`) | 14 | `ac_env.py:161-191`, значения делятся на константы из `obs_channels_info` (`ac_env.py:122-159,707-708`) |
| дальномеры (лучи до стен) | 11 | `sensors_ray_casting.py:9-10,212,237` (`N_RAYS=11`, ассерт на нечётность), делятся на `MAX_RAY_LEN=200` м (`ac_env.py:711`) |
| флаг "вне трассы" | 1 | `ac_env.py:716-719` |
| кривизна трассы вперёд | 12 | `CURV_LOOK_AHEAD_VECTOR_SIZE=12`, 300 м вперёд, `/CURV_NORMALIZATION_CONSTANT=0.1` (`ac_env.py:33-35,722-725`) |
| история последних 3 тактов steer/acc/brake | 9 | `PAST_ACTIONS_WINDOW=3`, `ac_env.py:30,737-740` |
| последнее применённое действие | 3 | `ac_env.py:746` |
| полная история 3 предыдущих "базовых+лучи" наблюдений | 3×25=75 | `ac_env.py:341-343,749-757` |

Итого по формуле в коде при дефолтном конфиге: 14+11+1+12+9+3+75 = **125**
(посчитано мной по коду, не найдено готовой константы — при других флагах в
`config.yml` число другое, формула в `ac_env.py:337-355`).

Нормализация — фиксированные константы-делители в словаре `obs_channels_info`
(`ac_env.py:122-159`), например `speed`/80 м/с (`TOP_SPEED_MS`, `ac_env.py:45`),
`RPM`/10000, `SlipAngle_*`/25°, `steerAngle`/450°. Константы жёстко зашиты в
код, не в конфиге.

История — не отдельная обёртка/frame-stack, а встроена прямо в вектор
наблюдения (см. таблицу выше): и сырые каналы за 3 такта, и steer/acc/brake за
3 такта одновременно.

## 4. Действия

- 3 непрерывные оси, всегда `[steer, acc(газ), brake]`, отдельными осями (не
  газ/тормоз одной осью): `Box(-1,1, shape=(3,))`, `ac_env.py:333-335`.
- `use_relative_actions: True` (`config.yml:60`) → действие агента — это
  **приращение**, а не абсолютная команда: `preprocess_actions`
  (`ac_env.py:408-414`) делает `new = current + action * rate_limit`, клип по
  физическим пределам (`controls_min/max_values`, из `steer_map.csv` для руля,
  ±1 для педалей). Ограничение скорости изменения: `max_steer_rate=900°/с`
  (`config.yml:73`, `ac_env.py:242,314-317`) для руля, фиксированное
  `±1200/100` условных единиц/такт для газа и тормоза (`ac_env.py:315-316`).
  Явного сглаживания (低-pass фильтра) сверх этого рейт-лимита нет.
- Масштаб перед отправкой: нормализованная команда `[-1,1]` (руль — в
  физических пределах из `steer_map.csv`, не всегда ±1) идёт как есть в
  `client.controls.set_controls(steer=,acc=,brake=)` (`ac_env.py:436`) →
  `DriverControls` (`ac_client.py:259-265`) → на стороне плагина
  `car_control.Controls.set_controls` переводит в диапазоны vJoy: steer→[0,2],
  acc/brake→[0,1] (`car_control.py:54-89`), финально в тики джойстика через
  `SCALE=16384` (`car_control.py:20,94-105`).
- **Коробка передач НЕ управляется RL-действием вообще.** `set_actions()`
  (`ac_env.py:425-437`) вызывает `set_controls` только с `steer/acc/brake` —
  `enable_gear_shift/shift_up/shift_down` остаются дефолтными
  (`False/0`, `ac_client.py:255-257`). В плагине есть готовый путь для
  секвентальной механики (`enable_gear_shift`→`onButtons` бит, `car_control.py:80-88`,
  `ego_server.py` `Client` :30-34), но он никем не вызывается со стороны
  среды/`train.py`. Обе инструкции по установке прямо рекомендуют **Automatic
  Gearbox: ON** и **Automatic Clutch: Enabled** (`INSTALL.md:91,93`,
  `data/data_collection_instructions.md:24,26`) — то есть штатный сетап форка
  — автомат, ручная коробка не реализована и не задействована.

## 5. Сброс

`AssettoCorsaEnv.reset()` (`ac_env.py:628-683`):
1. Сохранение статистики эпизода (`end_of_episode_stats`, если ещё не сохранено).
2. `client.reset(send_reset_at_start)` → `ac_client.py:157-163`: закрывает
   старый UDP-сокет, если `send_reset_at_start=True` (`config.yml:66`) шлёт TCP
   "reset" в плагин (`SimulationManagement.send_reset`, `ac_client.py:38-41`) —
   там **жёсткий `time.sleep(1)`** — плагин по этой команде вызывает
   `ac.ext_resetCar()` (телепорт/респавн через Custom Shaders Patch,
   `sensors_par.py:75-78,148-149`).
3. `controls.set_defaults()`, затем `setup_connection()` — переустановка UDP
   хэндшейка (`connect`→ждать `identified`, `ac_client.py:97-114`), таймаут
   каждого `recvfrom` 2с, ретраится в цикле без общего лимита.
4. 2 "холостых" `step()` с нейтральными действиями для заполнения истории
   (`ac_env.py:668-676`), затем ещё один реальный `step()` за первым наблюдением.

Итоговая длительность нигде не измеряется явно кодом, но по формуле:
жёсткий 1с sleep + время реконнекта (не лимитировано) + 3 такта по 40мс
(~120мс на 25Гц) ⇒ ориентировочно **~1.1-1.5с** при быстром реконнекте.

## 6. Termination / truncation

**Не возвращаются раздельно** — `step()` отдаёт классический 4-tuple
`(obs, reward, done, info)` (`ac_env.py:482`), один склеенный int `done`.
`done=1` выставляется в `expand_state()` (`ac_env.py:536-598`) по любому из:
AC сам завершил круг (`state["done"]`, `ac_env.py:541-544` — в коде прямо
комментарий `# TODO lap ended by AC.. see what to do here`, обработка не
доделана), `going_backwards` (сейчас захардкожен в 0, не реализован,
`ac_env.py:530,546-549`), выезд с трассы при
`enable_out_of_track_termination` (`ac_env.py:551-555`), превышен
`_max_episode_steps` (`ac_env.py:557-561`), превышен `max_laps_number`
(`ac_env.py:563-566`), низкая скорость дольше `TERMINAL_JUDGE_TIMEOUT=10`с при
`enable_low_speed_termination` (`ac_env.py:42-43,568-578`), либо `gap` больше
`max_gap` (`ac_env.py:581-583`).

Отдельно в `info`: `terminated=True` только для going_backwards/out_of_track/
low_speed (`ac_env.py:548,554,573`); `TimeLimit.truncated=True` только для
max_steps/max_laps (`ac_env.py:561,566`). У двух путей (AC's own lap-end,
gap-too-big) `done=1`, но **оба флага `terminated`/`truncated` остаются
False** — третья, необозначенная категория.

Для SAC-таргета используется НЕ `info['terminated']` напрямую, а отдельно
пересчитанный `masked_done` в цикле обучения
(`algorithm/discor/discor/agent.py:168-173`): `False`, если *собственный*
счётчик шагов эпизода агента `episode_steps+1 >= env._max_episode_steps`,
иначе — сырой склеенный `done`. Это НЕ читает `info['TimeLimit.truncated']` —
см. риски.

## 7. Награда

`get_reward()` (`ac_env.py:606-620`):
```
r = speed_kmh * (1 - |gap| / 12.0) / 300      # если use_reference_line_in_reward (default True)
r -= ||Δaction||₂ * penalize_actions_diff_coef  # если penalize_actions_diff (default False)
```
Зависит от `state['speed']`, `state['gap']` (посчитан по расстоянию до
racing line, `ac_env.py:499-504`) и от `actions_diff`, переданного из
`get_obs`. `out_of_track_calc`/`dist_to_border` в сигнатуру входят, но в
формуле не используются (`ac_env.py:606-611`).

**Функция — чистый метод класса `AssettoCorsaEnv`, конфиг-хука для подмены
нет** — заменить можно только сабклассом/переопределением `get_reward`, не
через `config.yml`. При этом код реально переиспользуется и для живой среды,
и для пересчёта по логам одним и тем же вызовом: `DataLoader.read_step`
(`assetto_corsa_gym/AssettoCorsaEnv/data_loader.py:100-102`) вызывает тот же
`env.get_obs()`/`env.get_reward()` на загруженной человеческой траектории —
т.е. "одна и та же функция для лайв и оффлайна" в этом форке соблюдено.
Реворд, впрочем, неявно зависит и от файлов трассы/racing line
(`self.track`, `self.racing_line`, загружены в `__init__`, `ac_env.py:287-292`),
не только от значений в самой строке телеметрии — для пересчёта по чужому
логу нужны те же файлы трассы.

Переход через старт/финиш: `LapDist = track_length * NormalizedSplinePosition`
(`ac_env.py:492`) — `NormalizedSplinePosition` берётся готовым от самой AC
(`ac.getCarState(..., NormalizedSplinePosition)`, `structures.py:73`), заворот
1→0 обрабатывается самой игрой, никакого дополнительного unwrap/разрыва в
коде `ac_env.py` не добавлено (в отличие от требования нашего CLAUDE.md
"обрабатывать явно, покрыть тестом" — здесь это не сделано explicit, просто
доверяет AC).

## 8. См. п.6 (SAC/target) и ниже (демонстрации)

Помимо `masked_done`, `next_state`, который пишется в буфер при `masked_done=False`
(truncation) — это реальное следующее наблюдение из среды
(`agent.py:164,180-182`: `next_state` берётся из фактического `self._env.step()`,
а НЕ из наблюдения после сброса) — это правильно с точки зрения "реальный
next_obs, не после reset".

## 9. Демонстрации (человеческие данные)

Формат записи — тот же, что и у самого RL: один Parquet-файл на эпизод,
`end_of_episode_stats()` (`ac_env.py:791-798`, `<ts>_states.parquet` +
`static_info.json`), либо легаси `.pkl` (`load_history`, `ac_env.py:866-885`
поддерживает оба). `DataLoader` (`data_loader.py:23-49`) собирает все
`*.pkl`+`*.parquet` из папки и проигрывает их шаг за шагом через
`env.get_obs`/`env.get_reward`/`env.inverse_preprocess_actions`
(`data_loader.py:80-123`), реконструируя `(obs, action, reward, next_obs, done, info)`
как будто это живая среда.

Список папок с демо — `ac_offline_train_paths.yml` (структура
track→car→список `{id, ...}`, парсится `get_path_for_track_car`/
`get_all_paths_in_file`, `data_loader.py:144-165`). Магония/RSR там
отсутствуют — файл содержит только те track/car, что уже размечены в
`AssettoCorsaConfigs`.

Загрузка в буфер — `Agent.load_pre_train_data`
(`algorithm/discor/discor/agent.py:287-314`), пишет в `EnsembleBuffer._offline`
(при этом `_online=False` по умолчанию, `replay_buffer.py:151,159-163`).

**Пропорция сэмплирования — жёстко 50/50, не конфигурируется**:
`EnsembleBuffer.sample()` всегда берёт `batch_size // 2` из offline и
`batch_size // 2` из online/offline (в зависимости от флага `_online`)
(`replay_buffer.py:171-183`). `train.py:126-127` включает `online(True)` сразу
после загрузки офлайн-данных и до начала обучения — то есть смешивание 50/50
действует весь тренинг, а не только на прогреве/претрейне.

## 10. Трасса

На трассу нужно 3 файла, прописанных в
`AssettoCorsaConfigs/tracks/config.yaml` (`ac_env.py:887-893`):
`track_file` (полилинии границ трассы, CSV), `ref_lap_file` (racing line +
опционально target speed, CSV), `track_grid_file` (пикл occupancy-grid с
шагом 0.1 м). **Magione в этом файле нет ни одной записи** — только
барселона/монца/silverstone/red bull ring/indianapolis/china/imola/laguna
seca/thunderhill/monaco (проверено `grep` по `config.yaml`).

`generate_track.ipynb` (`AssettoCorsaConfigs/tracks/generate_track.ipynb`) —
инструмент для генерации всех трёх файлов: требует **живого AC на нужной
трассе**, подключается через `assettoCorsa.make_client_only` (cell 2),
вызывает `client.export_track_and_racing_line()` (`ac_client.py:184-231`,
дёргает TCP `get_track_info`/`get_static_info` у плагина) → сохраняет
границы и racing line в CSV; затем считает кривизну (`curvature_splines`,
параметр `error` подобран вручную под каждую известную трассу, cell 12) и
**вручную зануляет** кривизну в начале/конце прямой по хардкод-индексам
(`else`-ветка хардкодит индекс `2934`, специфичный для конкретной уже
известной трассы, не универсальный); дальше строит occupancy-grid 0.1м через
point-in-quadrilateral по всем сегментам трассы (cells 17-31) и пиклит
результат. Ничего из этого не автоматизировано под новую трассу — по
markdown-комментарию в самом ноутбуке (cell 11): "adapt this to the track".

## 11. Машина

`AssettoCorsaConfigs/cars/<car>/` содержит ровно два файла:
`steer_map.csv` (2 строки: нормализованное действие ↔ градусы физического
руля, напр. dallara_f317 ±0.5342 ↔ ±240°, читается `ac_env.py:309-311,320-321`)
и `brake_map.csv` (11-точечная кривая нормализованного тормоза, грузится
`BrakeMap.load`, вызов в `data_loader.py:42`). Никаких параметров
двигателя/коробки/TC/ABS/массы в форке нет — это всё живёт внутри самого мода
машины в AC (`content/cars/<car>/...`), плагин их только читает через
`ac.getCarState`/`ui_car.json` (`CAR_MASS`/`CAR_DIM_*`,
`structures.py:216-227`).

Сейчас в конфигах только `dallara_f317`, `bmw_z4_gt3`, `ks_mazda_miata`
(проверено `ls`) — **Porsche 911 RSR 2017 отсутствует полностью**. Значения
для `dallara_f317` явно привязаны к мод-машине "RSR Formula 3"
(`INSTALL.md:114-115`, ссылка на overtake.gg) — это другой "RSR" (модмейкерская
группа RSR, Formula 3), не Porsche 911 RSR — совпадение в названии, не в
машине.

## 12. Логи

`end_of_episode_stats()` (`ac_env.py:788-856`) на каждый эпизод пишет: полный
сырой тик-телеметрический Parquet (`<ts>_states.parquet` — весь `self.state`
целиком, включая все производные каналы, не подмножество), один
`static_info.json` на сессию, и построчно копится `episodes_stats.csv`
(лаптаймы, число потерянных пакетов, средняя/макс скорость, лучший круг,
флаг termination) — `ac_env.py:848-852`.

Отдельно `discor.Agent` пишет TensorBoard-саммари (`SummaryWriter`,
`algorithm/discor/discor/agent.py:60`) и `summary.csv` по каждому эпизоду
(`agent.py:247`), плюс опционально Weights & Biases
(`train.py:96-100`, если `disable_wandb=False`).

На стороне плагина есть независимый `Telemetry` (`ego_server.py:8,109-110,190-193`,
не разбирался подробно) — пишет каналы AC с частотой
`telemetry_sampling_freq` (по умолчанию `0` = выключено, `config.py:10`) в
собственное хранилище, отдельно от Parquet-логов среды.

---

## Риски для RSR / Magione и ручной коробки

1. **Ни Magione, ни Porsche 911 RSR 2017 не существуют в этом форке** —
   ни в `AssettoCorsaConfigs/tracks/config.yaml`, ни в `AssettoCorsaConfigs/cars/`.
   Оба нужно создавать с нуля: трассу — вручную через `generate_track.ipynb`
   (не универсален, см. п.10), машину — новые `steer_map.csv`/`brake_map.csv`
   плюс сам мод RSR должен быть корректно установлен в AC (степень
   совместимости мода с `ac.getCarState`/`ui_car.json` не проверялась).
2. **Ручная коробка не реализована и не подключена нигде в RL-цепочке**
   (`ac_env.py`/`train.py` никогда не шлют `shift_up`/`shift_down`), а обе
   инструкции по установке рекомендуют Automatic Gearbox + Automatic Clutch.
   Провод до готового плагинного пути (`enable_gear_shift` в `car_control.py`)
   существует, но требует нового кода: action space, обвязка в `ac_env.py`,
   плюс отключение автокоробки/автосцепления в настройках AC.
3. **`train.py:72-73` жёстко требует CUDA** (`assert device.type == "cuda"`)
   — без рабочего GPU с CUDA 11.6 обучение не запустится вообще, только
   `--test`/аудит кода.
4. Чтение границ трассы в плагине (`structures.py`) само по себе
   помечено как ненадёжное для произвольных треков — по комментарию в коде
   протестировано только на Magione и Imola (`structures.py:254-257`). Это
   скорее хорошая новость для Magione конкретно, но подтверждено апстримом на
   их установке трассы, не на нашей.
5. Curvature-занижение в `generate_track.ipynb` хардкодит индексы под уже
   известные трассы; для Magione единственный доступный путь — generic
   `else`-ветка с чужим хардкод-индексом (`2934`), точно потребует ручной
   правки/проверки графика перед использованием.
6. **Двусмысленная truncation-семантика**: episode-конец по
   `state["done"]` (AC's own) и по `gap`-cutoff не помечается ни
   `terminated`, ни `truncated` в `info`, а SAC-таргет в
   `discor/agent.py:168-173` считает "усечение" по своему счётчику шагов, не
   по `info['TimeLimit.truncated']` — при остановке эпизода через
   `max_laps_number` до истечения `_max_episode_steps` это тихо
   классифицируется как жёсткое завершение (bootstrap занулится), хотя по
   смыслу это truncation. Стоит перепроверить/протестировать перед тем как
   доверять этому таргету для не-max-steps путей завершения.
7. Жёсткие требования к настройкам AC (50 FPS cap, конкретный
   `sampling_freq`, vJoy, Custom Shaders Patch) — при расхождении с
   документированным сетапом протокол молча ломает частоту/синхронизацию, а
   не падает с понятной ошибкой (`config.py:48-51` — единственный явный
   ассерт, остальное неявно).
