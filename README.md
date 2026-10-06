# SmolVLA в LIBERO и ROS2

Рабочий проект для тестового задания SmolVLA + LeRobot + ROS2.
Ноутбук используется для VS Code. На ПК-1 работают Docker, LIBERO и ROS2;
H100 предназначен прежде всего для обучения.

Актуальная конфигурация и результаты переноса на D: описаны в
[`setup/RECOVERY_2026-10-06.md`](setup/RECOVERY_2026-10-06.md).

## Запуск на ПК-1

Запустить Docker Desktop на ПК-1, затем `setup/Open-PC1.cmd` на ноутбуке.
Этот launcher запускает PowerShell-скрипт с разрешением только для своего процесса,
не меняя постоянную Execution Policy. Он открывает VS Code с отдельным
каталогом настроек `%LOCALAPPDATA%\SmolVLA-VSCode`, подключается к
`nlp-pc-2026` и открывает `/home/alexander/projects/smolvla-sim`.
Отдельные настройки нужны для Docker CLI проекта: этот параметр VS Code
имеет область application и игнорируется в workspace settings.
Обычные настройки редактора для учебных проектов сохраняются.

В терминале WSL:

```bash
cp -n .env.example .env
bash scripts/pc1.sh up -d
bash scripts/pc1.sh exec dev bash scripts/check.sh
```

Образ уже собран. `bash scripts/pc1.sh build` нужен после изменений Dockerfile;
перед пересборкой проверьте место на диске хранилища Docker Desktop и на C:.
Обычный запуск и Dev Containers используют только готовый образ: сборка вынесена
в `compose.build.yaml`, загрузка отсутствующего образа запрещена. Если образ
не найден, сначала проверьте Docker Engine; не запускайте сборку автоматически.
На ПК-1 используется Docker Desktop с WSL integration для Ubuntu. Перед работой
запустите Docker Desktop на ПК-1. Wrapper проверяет выбранный движок и не допускает
случайной работы с отдельным Docker Engine внутри Ubuntu.

После успешных проверок запустить один эпизод готовой модели:

```bash
bash scripts/pc1.sh exec dev bash scripts/eval_reference.sh
```

Это проверка окружения, а не измерение success rate: для отчёта требуются
все 10 задач и не менее 10 эпизодов на задачу, сравнение моделей и квантизации.
Обучение при настройке проекта автоматически не запускается.

В VS Code установить Dev Containers в удалённом контексте и выбрать
**Dev Containers: Reopen in Container**. Python контейнера: `/opt/venv/bin/python`.
Для обычного терминала с сохранением процесса: `bash scripts/open_tmux.sh`.
Отсоединение от tmux: Ctrl+B, затем D. Для длительных команд можно запускать
`bash scripts/pc1.sh exec -T dev ...` из tmux.

Проект использует отдельный Docker CLI config в `.runtime/docker-cli`, чтобы
не зависеть от старого credential helper Docker Desktop. Команды проекта
запускаются через `scripts/pc1.sh`. Параметр `GALLIUM_DRIVER=d3d12` применяется
только в WSL override; обычный Linux использует `compose.yaml` без override.

## Данные и воспроизводимость

Код ПК-1: `/home/alexander/projects/smolvla-sim`.
Веса, HF cache, видео и результаты: `/mnt/d/Robotics/smolvla-sim`, смонтирован
в контейнер как `/data`. Веса и датасеты не входят в Git или Docker-образ.
Дампы/кэш, перенесённые для освобождения C:, находятся отдельно в
`D:\Archives\robotics-setup-20261002`.

LeRobot закреплён на коммите `8fff0fde7c79f23a93d845d1a50e985de01f8b8a`
(v0.4.4). Все Python-зависимости перечислены в `requirements.lock`;
`requirements.ros.txt` закрепляет совместимую с colcon версию setuptools в ROS-образе.
Ревизии моделей и датасета указаны в `configs/artifacts.json`.
Версии ОС внутри образа сохраняются в `/opt/os-packages.txt`.
Для обновления зависимостей сначала меняются `.in`, затем пересоздаются lock
и повторяются проверки; существующие учебные окружения не используются.

## H100

Подключение с ноутбука: `setup/Open-H100.ps1`. Оно проходит через ПК-1 и его
Windows OpenSSH: приватный ключ остаётся на ПК-1. Прямой Linux SSH на ПК-1
может не работать из-за различий сетевого маршрута.

Единственный разрешённый корень работы:
`/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model`.
Каталог этого проекта внутри него: `smolvla-sim`.

```bash
cd /home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model/smolvla-sim
bash scripts/bootstrap_h100.sh
.venv/bin/python scripts/h100_run.py --mode smoke -- .venv/bin/python scripts/h100_cuda_check.py
```

Профиль H100 использует отдельный lock с CUDA 12.6 для проверенного драйвера
560.35.03; ПК-1 использует CUDA 12.8 для Blackwell. Python и код одинаковые.
GPU 0 запрещена. Обучение выбирает свободную GPU 2–7, smoke может использовать
GPU 1–7. Занятая карта не используется даже при явном `--gpu`.
Проверка свободной памяти не резервирует GPU для других пользователей сервера;
для длительных запусков нужно учитывать совместное использование ресурса.
Кэши, временные файлы и результаты H100 хранятся внутри `.runtime` проекта.

## Разработка

Исходный код: `src/smolvla_service`; ROS2-пакет: `ros2_ws/src/vla_bridge`.
CPU-проверки: `pytest -q` и `ruff check .`. Workflow GitHub Actions подготовлен,
но сам факт наличия файла не означает, что удалённый CI уже запускался.

На ноутбуке код лежит в `C:\Users\malne\Projects\smolvla-sim`, вне OneDrive.
После коммита `setup/Sync-PC1.ps1` отправляет изменения на ПК-1;
`setup/Sync-PC1.ps1 -Pull` забирает сделанные там коммиты. Используется собственный
bare Git-репозиторий на ПК-1; публичный репозиторий пока не создавался.
Перед сменой машины завершайте и коммитьте изменения. Синхронизация H100:
`bash scripts/sync_h100.sh` на ПК-1, только из чистого Git-дерева.

## Следующие этапы задания

- Дообучение на выбранных эпизодах LIBERO с обоснованными batch size и шагами.
- Оценка своей и готовой модели на одинаковых начальных состояниях.
- Сравнение n_action_steps 1, 10 и 50; BF16/INT8; latency p50/p95.
- Полная реализация sim_node и smolvla_node, замкнутый контур через ROS2.
- Видео, отчёт, таблицы и публикация репозитория для сдачи.

Первоначальные проверки: `setup/VALIDATION.md`. Актуальные проверки Docker
Desktop и инструкции восстановления: `setup/RECOVERY_2026-10-06.md`.
