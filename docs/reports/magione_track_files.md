# Файлы трассы Magione для среды

## Где что лежит

Сгенерированные файлы и инструмент живут в основном репо, не в
`third_party/assetto_corsa_gym`: `racetune/ac_configs/tracks/` (данные),
`racetune/tools/generate_track_offline.py` (генератор). Сабмодуль —
форк только ради кода апстрима (env/SAC), не хранилище наших
артефактов — если туда что-то писать, оно физически лежит в чужом
git-репозитории (`terracodum/assetto_corsa_gym`), а не у нас. Апстримные
примеры трасс (`monza` и т.д., в `third_party/.../AssettoCorsaConfigs/tracks/`)
не трогал — они часть форка, не наша работа.

Из-за этого `AssettoCorsaEnv`-у при использовании Magione нужно явно
передать `ac_configs_path=<repo_root>/racetune/ac_configs` (параметр уже
есть в апстриме, `assettoCorsa.py:48-58`, ничего в форке менять не
пришлось) — иначе он по умолчанию ищет конфиги в
`third_party/assetto_corsa_gym/assetto_corsa_gym/AssettoCorsaConfigs`, а
там Magione нет.

## Что сделано

### Разбор `generate_track.ipynb`

Читает из игры (`third_party/assetto_corsa_gym/assetto_corsa_gym/AssettoCorsaConfigs/tracks/generate_track.ipynb`,
через `client.export_track_and_racing_line`, `ac_client.py:184-231`):

- сокет `get_track_info`/`get_static_info` к плагину, живому в AC
  (`ac_client.py:187-188`) — плагин на своей стороне строит ответ из
  **одного статического файла игры**, не из физики текущей сессии:
  `content/tracks/<track>[/<config>]/ai/fast_lane.ai`, парсится
  побайтово в `structures.py:258-329` (`Track.__init__`). Единственные
  поля, которые реально приходят из живого API игры (`ac.*`), а не из
  этого файла — `static_info` (`structures.py:184-233`): `TrackName`,
  `TrackConfiguration`, `TrackLength` (`ac.getTrackLength`), `CarName` и
  т.д.

Пишет: `<track_full_name>.csv` (границы + идеальная линия) и
`<track_full_name>-racing_line.csv` (только идеальная линия),
дальше notebook строит occupancy grid (`Track`/`in_quadrilateral` из
`AssettoCorsaEnv/track.py`) и сохраняет `<track_full_name>_<cell_size>m.pkl`.

Поля `AssettoCorsaConfigs/tracks/config.yaml`, которые нужно завести на
новую трассу (`ac_env.py:887-893`): `track_name`, `track_configuration`,
`track_file`, `track_grid_file`, `ref_lap_file`, `TrackLength`. Ключ
верхнего уровня обязан совпадать с `static_info["TrackFullName"]`
(`ac_env.py:660`, assert).

### Почему офлайн, а не через живой AC

Все геометрические поля (`left_border_*`, `right_border_*`, `pos_x/pos_y`)
считаются в `structures.py:281-321` только из `fast_lane.ai` — сокет здесь
транспорт, не источник данных. Единственное живое-only поле —
`TrackLength` (`ac.getTrackLength`), и оно не критично: `ac_env.py:638`
перезаписывает его настоящим значением при первом `reset()` любого
реального прогона, а до этого момента нигде не используется для проверок.

Поэтому вместо ноутбука с живым клиентом написан
`racetune/tools/generate_track_offline.py` — порт-в-порт той же логики
(`parse_fast_lane` = `structures.py:281-321`, `export_track_and_racing_line`
= `ac_client.py:184-231`, grid = те же вызовы
`AssettoCorsaEnv.track.Track`/`in_quadrilateral`, что и в notebook-ячейках
15-31 апстримного `generate_track.ipynb`, апстримный notebook при этом не
трогал), запущенный прямо на установленной трассе:
`X:\SteamLibrarySSD\steamapps\common\assettocorsa\content\tracks\magione`
(путь — `docs/install_plugin.md:3`). Живая сессия AC для этого не
понадобилась — только установленный контент.

Сгенерировано (детали трассы 1754 точки, ~2.5 км):
- `racetune/ac_configs/tracks/magione.csv`
- `racetune/ac_configs/tracks/magione-racing_line.csv`
- `racetune/ac_configs/tracks/magione_0.1m.pkl` (occupancy grid, cell 0.1 м, не в git — тот же `.gitignore`-паттерн, что и у `monza_0.1m.pkl` в форке)
- `racetune/ac_configs/tracks/config.yaml` — запись `magione:`
  (`track_configuration` пуст — у Magione нет layout-подпапки, `ui_track.json`
  подтверждает единственную конфигурацию). Файл только с нашими треками,
  не копия полного апстримного `config.yaml`.
- `TrackLength: 2455.121337890625` — **не** `ac.getTrackLength()`, а
  cumulative `dist` последней точки `fast_lane.ai`; заглушка, безопасная
  по причине выше. Официальная длина по `ui_track.json` — 2507 м
  (ожидаемое расхождение ~2%, разные методики замера).
- Кривизна идеальной линии (`curvature_splines`, `error=1.0`) на границах
  уже мала (индекс 0: -0.007, индекс -1: 0.01, относительно пика в
  поворотах 0.057) — проверено вручную (см. ниже), форсировать в 0 не
  потребовалось. В апстримный `generate_track.ipynb` это не заведено
  (файл не трогаю), просто зафиксировано здесь как результат проверки.

### Система координат — найдена и подтверждена ловушка

Экспорт трассы (`structures.py:311-312,321`) кладёт в `*_x`/`pos_x`
**сырую мировую Z** (без инверсии), а в `*_y`/`pos_y` — **сырую мировую X**.
Рекордер лабов (`parcer/lap_recorder.py:205`) инвертирует знак при записи:
`car_z = -raw_z`, `car_x` пишется как есть (`lap_recorder.py:203`). Это
**другая** ось расхождения, чем уже описанная в `CLAUDE.md` ловушка со
старым CSV (там про сам факт инверсии в рекордере; здесь — про то, что
экспорт трассы её не делает, и что оси x/y при этом ещё и переставлены
местами).

Подтверждено эмпирически (не только по чтению кода): bounding box
`fast_lane.ai` (x: −167.15…137.49, z: −425.70…395.28) почти точно совпадает
с bounding box `data/lap_2026-05-27_13-23-37.car_z_fixed.csv`
(`car_x`: −169.31…137.81, `car_z`: −396.85…426.68, где `-car_z` даёт
−426.68…396.85 — совпадает с диапазоном z с точностью ~1.5 м). Это заодно
доказывает то, что раньше нигде явно не было зафиксировано: **старая
запись `lap_2026-05-27_13-23-37.csv` сделана на Magione**, а не на
произвольной трассе.

Итоговое маппирование для наложения: `track_x = -car_z`, `track_y = car_x`.
Использовано в `notebooks/magione_track_verification.ipynb`.

### Ноутбук-проверка

`notebooks/magione_track_verification.ipynb` — occupancy grid + обе
границы + идеальная линия + человеческий круг на одном графике,
выполнен, вывод сохранён в файле.

Файл `lap_2026-05-27_13-23-37` — не один круг, а цельная сессия из 7
кругов (`lap` 4–10, по 1.9–2.2k строк на круг, `lap` 10 короткий — 119
строк, похоже на оборванный последний круг). Первая версия проверки
накладывала все круги одной линией — это маскирует, какой круг даёт
отклонение. Добавлена отдельная ячейка с разбивкой по `lap` (разные
цвета): **6 из 7 кругов (4, 5, 6, 8, 9, 10) идут внутри границ по всей
трассе**, включая правую шпильку. Короткая петля за границей у этой
шпильки (~x=300, y=−170) — чёткий одиночный выброс **круга 7**, не
систематика: остальные круги через тот же поворот проходят чисто, значит
это реальный съезд/разворот в записи, а не баг координат или границ.

**Готово когда** (из постановки задачи) — выполнено, причём проверено не
«в среднем по всем кругам сразу», а по каждому кругу отдельно.

## Побочная находка (не по теме задачи, но важно)

При первом запуске ноутбука через живое ядро Jupyter в `p309` любой
`import matplotlib.pyplot` падал: `AttributeError: 'RcParams' object has
no attribute '_get'`. Причина: `environment.yml` пинит `matplotlib==3.5.3`,
но `matplotlib-inline` не запинен, тянется последней версией (была
0.2.2) — она дёргает приватный метод `rcParams._get`, которого нет в
matplotlib 3.5.3. Ломало **любой** notebook в `p309`, использующий
matplotlib (`generate_track.ipynb`, `generate_visualizations.ipynb`,
`notebooks/*`), не только новый.

Пофикшено: `matplotlib-inline==0.1.6` запинен в `environment.yml`, версия
понижена в уже установленном `p309`. После фикса ноутбук выполняется без
ошибок (см. выше).

## Не проверено / открытые вопросы

- **Live-путь не проверялся.** Офлайн-генерация даёт то же самое, что дал
  бы `generate_track.ipynb` через живой сокет (данные — из одного и того
  же файла), но байт-в-байт эквивалентность не подтверждена реальным
  прогоном через плагин — только через чтение кода и совпадение bounding
  box с независимым источником (лог человека). Если хочется live-сверки:
  запустить AC, Practice на Magione (машина любая), включить
  sensors_par, прогнать `generate_track.ipynb` штатно — совпадут ли
  `static_info["TrackLength"]`/`TrackFullName` с тем, что сейчас в
  `config.yaml`. Не блокирует задачу.
- **Именование left/right в `structures.py:307-312` перепутано** (левая
  граница на деле строится из правого смещения и наоборот) — это уже
  было так до задачи, поведения не меняет (`track.py:88-94` строит quad
  из пар точек безотносительно того, как назвали сторону), но если
  когда-то понадобится геометрический смысл "лево"/"право" отдельно —
  учесть.
- `generate_track_offline.py` — общий инструмент (не привязан к
  Magione), но обкатан пока только на одной трассе.
