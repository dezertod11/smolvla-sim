# Сеть Codex в Dev Container

12 октября 2026: вход в Codex завершался `token_exchange_failed`.
В журнале расширения зафиксирован transport failure обращения к
`https://auth.openai.com/oauth/token`. HTTPS из контейнера обрывался до HTTP-ответа
также для GitHub. Вход по device code испытывал ту же сетевую проблему.

Рабочий Happ обнаружен на ноутбуке: Xray слушает HTTP-порт 10809.
На ПК-1 интерфейс Happ был открыт, но Xray/слушатель 10809 отсутствовал.
Наличие процесса Amnezia само по себе не доказывает, что он обслуживает VPN.
Системный прокси ПК-1 указывал на неработающий в момент проверки 127.0.0.1:10809.

## Рабочий маршрут

VS Code/Codex в контейнере → `host.docker.internal:18089` → Windows OpenSSH ПК-1
→ зашифрованный SSH-туннель → `127.0.0.1:10809` на ноутбуке → Happ.

`setup/Open-PC1.cmd` запускает `Start-PC1Proxy.ps1`. Один скрытый PowerShell worker
держит SSH-туннель и повторяет соединение после сетевого сбоя с паузой 10 секунд.
На ПК-1 listener привязан только к `127.0.0.1`; LAN-порт и правила firewall
не открываются. Используются существующие SSH-ключ и проверенный host key.
TLS проверяется обычным образом; токены и ключи не копируются.

Прокси задан через `remoteEnv` в `.devcontainer/devcontainer.json`:
переменные действуют в VS Code, Codex, новых терминалах, задачах и отладчике.
Обычный `docker exec`, соседние контейнеры, Windows, WSL и H100 не перенастраиваются.
Локальные адреса исключены через `NO_PROXY`. Скачивания из терминала VS Code
также идут через ноутбук; учитывайте это для больших датасетов.

## Ежедневная работа

1. Docker Desktop работает на ПК-1; Happ подключён на ноутбуке.
2. Открыть `setup/Open-PC1.cmd` двойным щелчком.
3. В Codex выбрать Sign in with ChatGPT, если ещё не выполнен вход.

Ноутбук должен оставаться включённым. Сон или отключение Happ прерывает запросы
Codex; worker восстанавливает SSH после пробуждения, но прерванную операцию
может потребоваться повторить. Закрытие VS Code не останавливает worker.
Это соединение для интерактивной разработки; автономное обучение на H100
не должно зависеть от ноутбука или этого прокси.

После перезагрузки ноутбука worker запускается только через launcher,
глобальная автозагрузка не добавлена. При запуске напрямую через Recent в VS Code
нужно, чтобы worker уже работал. Если Happ выключен, launcher показывает
предупреждение и всё равно позволяет открыть проект для работы с кодом.

## Проверка и остановка

В новом терминале VS Code в контейнере:

```bash
curl -sS -o /dev/null --connect-timeout 5 --max-time 15 \
  -w 'HTTP=%{http_code} TLS=%{ssl_verify_result}\n' \
  https://auth.openai.com/oauth/token
```

GET к этому endpoint не выполняет вход. Ответ `405`, TLS `0` означает,
что HTTPS работает, а endpoint ожидает другой HTTP-метод. Это не проверка
учётной записи; успешный вход нужно подтвердить в Codex.

Остановить только созданный туннель, в PowerShell ноутбука:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\malne\Projects\smolvla-sim\setup\Start-PC1Proxy.ps1 -Stop
```

Повторный `Open-PC1.cmd` запустит его снова. Технический журнал и PID worker:
`.runtime/codex-network/` на ноутбуке (исключены из Git).

## Откат

Остановить worker командой выше, убрать `remoteEnv` из devcontainer.json и вызов
Start-PC1Proxy.ps1 из Open-PC1.ps1, затем переподключить контейнер.
Старый devcontainer.json сохранён на ПК-1:
`.runtime/codex-network-repair/devcontainer.before.json`.
Изменения Dockerfile/образа, сетевых настроек VPN и перезапуск WSL не нужны.

Официальная документация:
[VS Code remoteEnv](https://code.visualstudio.com/remote/advancedcontainers/environment-variables),
[вход в Codex](https://learn.chatgpt.com/docs/auth).
