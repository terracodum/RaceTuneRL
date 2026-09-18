# Прогон готового чекпоинта: Monza + BMW Z4 GT3

Цель — не тюнинг, а проверка, что вся обвязка (плагин, окружение,
train.py) реально работает: грузим готовый чекпоинт авторов форка и
смотрим, едет ли машина и получается ли заявленный лаптайм (~112.1 с,
`third_party/assetto_corsa_gym/README.md:157`).

## Что уже сделано (не требует AC)

- Скачан occupancy grid трассы: `AssettoCorsaConfigs/tracks/monza_0.1m.pkl`
  → лежит в `third_party/assetto_corsa_gym/assetto_corsa_gym/AssettoCorsaConfigs/tracks/`
  (ровно туда, куда его грузит `ac_env.py:887-893` по `config.yaml:13`).
- Скачан чекпоинт `step_05400000` (policy_net.pth, online_q_net.pth,
  target_q_net.pth) →
  `third_party/assetto_corsa_gym/results/checkpoints/data_sets/monza/bmw_z4_gt3/20241108_SAC/model/checkpoints/step_05400000/`.
  Папка `results/` внутри submodule в `.gitignore` форка — файлы туда не
  попадут в git по-любому, но на всякий случай: **не делай `git add` внутри
  `third_party/assetto_corsa_gym`** — это чужой форк, коммитим только из
  RaceTuneRL.
- Оба файла — данные (веса модели, геометрия трассы), не код форка — правило
  "не менять логику upstream" не нарушено.

## Что нужно сделать в Assetto Corsa

Общая настройка плагина (vJoy, Custom Shaders Patch, 50 FPS, Hotlap-режим,
ассисты) — по `docs/install_plugin.md`, если ещё не сделано. Ниже —
специфика именно для этого прогона.

1. **Трасса: Monza** — это встроенная трасса AC (`monza`), отдельно качать
   не нужно.
2. **Машина: BMW Z4 GT3** (внутренний id должен быть ровно `bmw_z4_gt3`
   — так его ищет `ac_env.py:661`: `static_info["CarName"] == self.car_name`,
   при несовпадении упадёт с понятной ошибкой "Car name mismatch" сразу при
   старте, а не молча). В `INSTALL.md`/`README.md` форка эта машина нигде
   не упомянута как мод для отдельного скачивания (в отличие от Dallara F317,
   `INSTALL.md:112-120`) — похоже на встроенный в AC/DLC контент (Dream Pack),
   но это не проверено по коду, только по отсутствию инструкции. Если в
   списке машин в игре её нет — значит нужен доп. DLC/мод, в форке про это
   ничего не написано.
3. Challenge → Hotlap, трасса Monza, машина BMW Z4 GT3, старт сессии — как
   обычно перед тем как что-то из среды подключается.
4. Дождаться, пока плагин поднимет сокет-сервер (лог в консоли AC:
   `[EGO SERV] Start ego server socket on: ...`).

## Команда запуска

Из `p309` (conda), **рабочая директория — `third_party/assetto_corsa_gym`**
(train.py грузит `config.yml` и добавляет пути относительно текущей папки,
`train.py:12,27`):

```
conda activate p309
cd third_party\assetto_corsa_gym
python train.py --test disable_wandb=True --load_path "X:\Coding\work\RaceTuneRL\third_party\assetto_corsa_gym\results\checkpoints\data_sets\monza\bmw_z4_gt3\20241108_SAC\model\checkpoints\step_05400000" AssettoCorsa.track=monza AssettoCorsa.car=bmw_z4_gt3
```

Пояснения:
- `--test` — не обучает, только `agent.evaluate()` (`train.py:136-139`),
  `set_eval_mode()` выставляет 4 круга на эпизод (`ac_env.py:895-897`,
  `config.yml:54` `eval_number_of_laps: 4`, включая невалидный выездной круг).
- `disable_wandb=True` — оверрайд конфига через CLI (`config.yml:9`, парсится
  `train.py:46-47`), чтобы не упереться в логин Weights & Biases на первом же
  прогоне. Без него `train.py:97-100` попытается создать wandb-логгер.
- `--load_path` — грузятся только веса сети (`train.py:132-134`, при
  `--test` `load_buffer=False`) — файла `replay_buffer.pkl` у нас нет и он не
  нужен.
- Путь к чекпоинту без завершающего `\` — код сам добавит разделитель
  (`train.py:36`).

## Что прислать обратно

1. Консольный вывод команды целиком (или последние ~50 строк, где должны
   быть числа кругов и `done evaluation`).
2. Путь к созданной папке прогона:
   `third_party\assetto_corsa_gym\outputs\<timestamp>\` — она создаётся
   автоматически (`train.py:49-56`, `config.work_dir: null` в `config.yml:1`).
3. Вывод `python scripts\extract_lap_times.py` (без аргумента — сам найдёт
   последний прогон в `outputs\`).

## Если что-то пошло не так

- **Ошибка сразу при старте про несовпадение трассы/машины/частоты**
  (`ac_env.py:659-661`) — трасса/машина в AC выставлены не те, или FPS-лимит
  не 50.
- **Машина не едет вообще** (стоит на месте) — вероятнее всего vJoy не
  выбран активным контроллером в Options → Controls
  (`docs/install_plugin.md`, п.6), либо `enable_gear_shift`/автокоробка не
  включена в AC (агент никогда не переключает передачи сам — см.
  `docs/acgym_audit.md`, п.4 — без автокоробки/автосцепления машина
  физически не сможет разогнаться после старта на 1-й передаче).
- **Круг заметно медленнее ~112 с** — возможные причины на разбор в отчёте:
  несовпадение частоты (`ego_sampling_freq` в `config.yml` и в плагине
  должны быть 25 Гц с обеих сторон, `ac_env.py:659`), другая версия/сборка
  мода машины BMW Z4 GT3 (другие `steer_map.csv`/`brake_map.csv` физически
  привязаны к конкретной версии мода — `docs/acgym_audit.md`, п.11), другие
  настройки ассистов (TC/ABS/автосцепление должны быть выключены/включены
  ровно как в таблице `docs/install_plugin.md`, п.9), либо GPU слишком
  медленный/просевший FPS ниже 50 из-за того, что update_model на каждом шаге
  (`discor/agent.py:154-161`) не успевает и агент "теряет" реальное время
  между тиками (см. `docs/acgym_audit.md`, п.2).
