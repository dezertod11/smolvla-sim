# Матрица приёмки

Состояние требований исходного задания на итоговом коммите.

| Требование | Статус | Доказательство |
|---|:---:|---|
| Сборка по README за 3-4 команды | ✅ | Свежий публичный clone, bootstrap, SHA256 checkpoint и Compose: `artifacts/results/ros2-own-final/fresh-clone-verification.json` |
| Compose поднимает два ROS2-узла и запускает эпизод | ✅ | `compose-runtime.typescript`: `success=True`, 159 действий, exit code 0 |
| LeRobot, Python и системные зависимости закреплены | ✅ | `docker/Dockerfile`, `requirements.lock`, `requirements.ros.txt`, `configs/artifacts.json` |
| Веса отсутствуют в Git и Docker image | ✅ | Публичный GitHub Release, внешний `/data/models/own-final`, SHA256 manifest |
| Конфиг, loss curve и доступный checkpoint | ✅ | `configs/train_libero_object.json`, `artifacts/results/training`, release `smolvla-libero-object-v1` |
| Объяснены обучаемые и замороженные части | ✅ | README, раздел «Обучение»; 99 880 992 из 450 046 176 параметров обучаются |
| Своя и reference-модель оценены на общих эпизодах | ✅ | 10 задач × 10 эпизодов, seed 10000+, `evaluation_summary.json` |
| `n_action_steps` 1, 10 и 50 | ✅ | 85%, 97% и 71%; время эпизода приведено в общей таблице |
| GPU/CPU latency, warm-up, synchronize, p50/p95 | ✅ | `scripts/benchmark_policy.py` и три benchmark JSON |
| BF16/INT8: размер, latency, память, success | ✅ | Единая таблица README; BF16 97/100, INT8 0/100 |
| Рекомендация для Jetson Orin 16 ГБ | ✅ | BF16, `n_action_steps=10`; обоснование и ограничения приведены |
| Inference не блокирует executor | ✅ | `AsyncInference`, single-flight worker и CPU unit-тесты |
| Closed loop работает через ROS2 topics | ✅ | Две камеры, состояние и действие; Compose episode `success=True` |
| Пропавшие данные обрабатываются без падения | ✅ | Freshness watchdog и периодическое предупреждение в `smolvla_node` |
| Параметры передаются из YAML через launch | ✅ | instruction, checkpoint, precision, device, steps, frequency и timeout |
| Unit-тесты без GPU и весов | ✅ | Изображение, действие, YAML, async inference, метрики и mock quantization |
| GitHub Actions: Ruff и pytest CPU | ✅ | Workflow `.github/workflows/ci.yml` |
| Видео успеха, неуспеха и Compose | ✅ | Четыре MP4 в `artifacts/videos` |
| Краткий отчёт на одну страницу | ✅ | `output/pdf/smolvla_report.pdf` |

Все блокирующие пункты исходного чек-листа закрыты. Измерения относятся к
`libero_object`; перенос на реального робота и Jetson Orin требует отдельной
валидации, как указано в README.
