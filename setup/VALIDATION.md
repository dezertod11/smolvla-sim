# Паспорт окружения — 2026-10-02

## Где работать

| Узел | Назначение | Каталог |
| --- | --- | --- |
| Ноутбук Windows | VS Code, локальная копия исходников | `C:\Users\malne\Projects\smolvla-sim` |
| ПК-1, Ubuntu 24.04 в WSL2 | Docker, RTX 5070 Ti 16 ГБ, LIBERO, ROS2 Jazzy | `/home/alexander/projects/smolvla-sim` |
| ПК-1, диск D: | Модели, кэши, видео, результаты | `D:\Robotics\smolvla-sim` |
| H100 | Отдельное окружение обучения | `/home/jovyan/shares/SR006.nfs2/spiridonov/malnev_world_model/smolvla-sim` |

## Проверено на ПК-1

- NVIDIA Container Toolkit 1.20.1 настроен; `docker run --gpus all ... nvidia-smi` видит GPU.
- Образ `smolvla-sim:dev` собран, сервис `dev` запускается через Compose.
- PyTorch 2.7.1+cu128: прямой проход и backpropagation на RTX 5070 Ti.
- bitsandbytes 0.48.2: настоящая операция Linear8bitLt на CUDA.
- MuJoCo 3.3.2: EGL-рендер, renderer `D3D12 (NVIDIA GeForce RTX 5070 Ti)`.
- LIBERO: загрузка сцены libero_object task 0, reset, шаги симуляции,
  изображения с двух камер. Это не программный renderer llvmpipe.
- Готовая SmolVLA `HuggingFaceVLA/smolvla_libero`: один эпизод task 0,
  seed 0, n_action_steps=10 завершён успешно (reward=1, success=True).
  Время evaluation около 24,3 с, без первоначальной загрузки модели.
- ROS2 Jazzy: обмен семимерным массивом; отдельно выполнены colcon build
  и launch двух процессов пакета vla_bridge, оба завершились штатно.
- CPU pytest: 10 passed. Ruff: All checks passed. `pip check`: конфликтов нет.
- Dev Containers CLI 0.89.0: read-configuration и up завершились с outcome=success,
  рабочий каталог `/workspace`, пользователь 1000. Лог: `devcontainer-up.log`.

Один успешный эпизод проверяет работоспособность окружения. Это не результат
полной оценки на 100 эпизодах, не замер latency модели и не дообученная нами модель.
INT8-проверка проверяет библиотеку; квантизация всей SmolVLA ещё предстоит.

Логи лежат в `D:\Robotics\smolvla-sim`: `runtime-check.log`,
`libero-check.log`, `ros-package-check.log`, `reference-check.log`.
Видео: `outputs/reference-smoke-20261002T151301/videos/libero_object_0/eval_episode_0.mp4`.

## H100

Проверены доступ по существующему ключу ПК-1, Ubuntu/Python, драйвер 560.35.03,
наличие восьми H100 80 ГБ и около 1,6 ТБ свободного места на рабочем томе.
Используется PyTorch 2.7.1+cu126 и отдельный полный lock зависимостей.
Установка завершилась успешно; проверка всех 165 пакетов не нашла конфликтов.
На свободной физической GPU 3 выполнены BF16 forward/backward и синхронизация
CUDA: `PASS 2.7.1+cu126 NVIDIA H100 80GB HBM3`.
CPU-проверки на H100 также прошли: 10 pytest, Ruff без замечаний.
Ключи в репозиторий не копируются. GPU 0 запрещена; запуск через h100_run.py
выбирает свободную разрешённую карту непосредственно перед процессом.

Соединение через Windows OpenSSH ПК-1 периодически не проходит SSH banner;
это отдельное ограничение доступности, не ошибка CUDA. При timeout повторите
подключение позже. Прямой SSH из WSL на момент проверки не работал стабильно.

## Место и сохранность существующих проектов

Старые WSL crash dumps, Windows pip cache и старые распакованные файлы
установщика VS перенесены в `D:\Archives\robotics-setup-20261002`.
Каждый файл проверен по SHA256 перед удалением исходника; журнал
`moved-files.jsonl` позволяет найти сохранённую копию. Архив не удалён.

После создания окружения свободно около 7,3 ГБ на C: и 117 ГБ на D:.
WSL VHDX всё ещё находится на C:. Его виртуальный `df /` не отражает
свободное место Windows! Новые большие сборки требуют дополнительного места.
Рекомендуемый следующий шаг по хранению — перенести WSL на D: в согласованное
окно остановки. Это не выполнялось, чтобы не прерывать учебные процессы.

Docker перезапущен при настройке GPU, когда работающих контейнеров не было.
Существующие Jupyter, WSL и учебные venv не перезапускались и не изменялись.
Резервная копия Docker-настроек:
`/home/alexander/robotics-setup/backups/20261002T174338`.

## Границы готовности

Окружение и каркас подготовлены. Полный sim_node/smolvla_node, дообучение,
оценка всех задач, квантизация модели и итоговый отчёт остаются этапами задания.
Полный датасет автоматически не скачивался. GitHub CI описан в workflow,
но удалённый GitHub-репозиторий и запуск Actions пока отсутствуют.
Git-синхронизация ноутбук → ПК-1 и ПК-1 → H100 проверена. История хранится
также в bare-репозитории `/home/alexander/robotics-setup/git/smolvla-sim.git`.
Отдельная tmux-сессия `smolvla` существует; прежние cv/nlp/jupyter сохранены.
Настройки VS Code и Dev Container созданы; GUI-открытие редактора и reconnect
самого VS Code не проверялись. Запуск контейнера проверен через CLI расширения.
