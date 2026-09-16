# Подключение assetto_corsa_gym

## Что сделано

- `requirements.txt` заполнен реальными зависимостями notebooks/ (импорты
  проверены по коду ноутбуков): `pandas`, `numpy`, `matplotlib`, `seaborn`,
  плюс `ipykernel` (нужен для исполнения `.ipynb`). Версии зафиксированы по
  текущему рабочему окружению (`pip show`).
  `parcer/lap_recorder.py` использует только stdlib (`mmap`, `ctypes`,
  `struct`, `csv`, `time`, `os`, `datetime`) — новых зависимостей не добавляет.
- Форк `dasGringuen/assetto_corsa_gym` создан под `terracodum`:
  https://github.com/terracodum/assetto_corsa_gym (через `gh repo fork`,
  после того как человек авторизовал `gh auth login`).
- Подключён как submodule: `git submodule add
  https://github.com/terracodum/assetto_corsa_gym.git third_party/assetto_corsa_gym`
  → `.gitmodules` создан, `third_party/assetto_corsa_gym` склонирован.
- README дополнен: Windows-only заметка со ссылкой на
  `parcer/lap_recorder.py:104` (`mmap.mmap(..., tagname=...)`), ссылка на
  форк-submodule, инструкция `git clone --recursive` /
  `git submodule update --init --recursive`.
- Версии Python 3.9.13 / PyTorch 1.12.1 / CUDA 11.6, упомянутые в README
  RaceTuneRL как версии submodule, проверены по коду submodule:
  `third_party/assetto_corsa_gym/README.md:116` (`conda create -n p309
  python=3.9.13`) и `:122` (`conda install pytorch==1.12.1 cudatoolkit=11.6`).

## Что не сделано

- Ничего из первоначального запроса не осталось не сделанным.
- В `third_party/assetto_corsa_gym` ничего не менялось (правило 2) — только
  добавлен как submodule, коммит upstream не трогали.

## Открытые вопросы

- Нужно ли пинить конкретный commit/branch форка в submodule, или оставить
  как есть (HEAD форка на момент добавления submodule)?
- Форк сейчас — обычный fork без изменений относительно `dasGringuen/assetto_corsa_gym`
  на момент создания; если нужно синхронизировать/уходить в divergence — не
  решал, это дизайн-вопрос.

## Окружения (добавлено по ходу)

Два раздельных Python-окружения, как и должно быть — версии несовместимы
между собой (numpy 1.23.3/pandas 1.4.4 из submodule сломали бы EDA-ноутбуки,
где numpy 2.1.3/pandas 3.0.2, и наоборот):

- **Системный Python 3.12.9** — для `notebooks/` и `parcer/`. `pip install -r
  requirements.txt` (корень репо) — всё уже стояло, конфликтов не было.
- **conda env `p309`** — для `third_party/assetto_corsa_gym`. Создан через
  `conda create -n p309 python=3.9.13`; conda сам обновил его до `3.9.23`
  при установке pytorch/cudatoolkit (conda-forge build) — отклонение от
  буквального "3.9.13" из CLAUDE.md, но в рамках 3.9.x.

### Проблемы при установке и как решены

1. **`gym==0.21.0` не собирается** — метаданные пакета (`extras_require`)
   не проходят строгий парсинг pip >= 24.1. Фикс: `pip<24.1` внутри env
   `p309` (сам пакет `gym` не трогали).
2. **PyTorch 1.12.1 через `conda install -c pytorch -c conda-forge`
   (команда из upstream README) ставился, но крашился при импорте**
   (`OSError: ...shm.dll`) — conda-forge подтянул `mkl-2025.3.1`, несовместимый
   по ABI с бинарником pytorch 1.12.1, собранным под старый mkl. Фикс:
   снёс conda-пакеты pytorch/cudatoolkit/mkl, поставил `torch==1.12.1+cu116`
   через официальный pip-wheel (`--extra-index-url
   https://download.pytorch.org/whl/cu116`) — тот же биты, без конфликта с
   conda-форджевым mkl.
3. Побочный эффект от предыдущего пункта — `conda remove` снёс файл
   `typing_extensions`, которым также пользовался pip (общий site-packages).
   Фикс: `pip install --force-reinstall typing_extensions==4.3.0`.
4. **`pybullet` не установлен.** В `requirements.txt` пакет не запинен,
   актуальная версия на PyPI не публикует wheel под Python 3.9 + Windows —
   pip пытается собрать из исходников, для чего на машине нет `cl.exe`
   (не установлены MSVC Build Tools). Проверил версии 3.0.9–3.2.7 — ни у
   одной нет подходящего wheel. Не решал сам: либо ставить Visual Studio
   Build Tools (C++ workload, несколько ГБ) и собирать из исходников, либо
   искать conda-forge сборку. Оставлено как открытый вопрос — pybullet
   пропущен, остальной `requirements.txt` submodule установлен полностью.
5. **Конфликт `wandb==0.12.16` vs unpinned `tensorboard`.** `tensorboard`
   не запинен в `requirements.txt`, поставилась последняя версия (2.21.0),
   требующая `protobuf>=6.31`; сгенерённые `.proto`-файлы `wandb` 0.12.16
   собраны под старый protobuf и падают на новом (`TypeError: Descriptors
   cannot be created directly`). Фикс: `tensorboard==2.10.1` — версия той же
   эпохи (2022), что и остальной стек (torch 1.12.1/gym 0.21.0), тянет
   совместимый protobuf сама. Это не в `requirements.txt` submodule и не
   зафиксировано отдельным файлом версий с нашей стороны — если нужно
   сделать это воспроизводимым, надо решить, куда пишем фактические версии
   (`environment.yml` в RaceTuneRL, не трогая submodule).

### Проверено

`python -c "import numpy, torch, gym, pandas, matplotlib, tensorboard, wandb,
scipy, sklearn"` в env `p309` — проходит без ошибок.
`torch.cuda.is_available()` → `True`.
