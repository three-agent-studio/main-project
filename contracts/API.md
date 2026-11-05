# API и правила расширения

Владелец общих контрактов — участник №1. Изменения согласуются с потребителями №2/№3.
OpenAPI генерируется из DRF serializers/views командой `python manage.py spectacular --file ../contracts/openapi.generated.yaml --validate --fail-on-warn`.
CI сохраняет схему как артефакт; ручная копия схемы не должна расходиться с сервером.

## Реализованный фундамент

| Метод | Адрес | Доступ и ответ |
|---|---|---|
| GET | `/health/live/` | Публичный, `{"status":"ok"}` |
| GET | `/health/ready/` | Проверка БД; 200 или 503, без деталей подключения |
| GET | `/api/v1/csrf/` | `{"csrfToken":"…"}` и CSRF cookie; не сохранять в localStorage |
| GET | `/api/v1/me/` | Только сессия; id, username, student_profile (объект или null) |
| GET/POST | `/auth/login/` | Django LoginView, HTML-форма и CSRF; после входа `/profile` |
| POST | `/auth/logout/` | CSRF обязателен, сессия удаляется, redirect на `/` |
| GET | `/api/v1/schema/` | Только административный пользователь |

`student_profile`: full_name, faculty, programme, course, group. Профиль доступен только для чтения.
`is_staff` означает доступ к Django Admin, **не роль сотрудника деканата**. Ограниченную роль сотрудника и его факультет реализовать в #5/#8.

## Общие соглашения

- Только JSON для `/api/v1/`; аутентификация — серверная сессия, 403 при отсутствии сессии.
- Ошибки DRF: `{ "error": { "status": 403, "details": { "detail": "…" } } }`.
  Не-API маршруты (CSRF middleware, HTML login, 404 URL) могут вернуть HTML: клиент учитывает Content-Type.
- Списки: `{count, next, previous, results}`; по умолчанию 25 записей на страницу.
- Время — ISO 8601 с часовым поясом, хранение UTC, показ в часовом поясе вуза.
- Владелец определяется по request.user. UUID/скрытый UI не заменяют авторизацию.
- List/detail/update/delete фильтруются по области доступа; чужой объект — 404.
- Cookie/CSRF передаются только в пределах своего origin. POST/PATCH/DELETE требуют X-CSRFToken.
- Клиент не назначает себе роль, группу, владельца заявки или статус.

## Следующие контракты (ещё не реализованные endpoints)

- №1, #7: `/api/v1/lessons/?from=…&to=…`, `/api/v1/assessments/`.
- №3, #8: `/api/v1/requests/`, `/api/v1/requests/{id}/`, отдельное действие сотрудника для статуса.
- №3, #9: `/api/v1/notifications/` и действие отметки прочтения.

Имена и DTO этих будущих endpoints нужно согласовать в #3 до интеграции.
Статусы заявок: submitted → in_progress → completed/rejected. История и уведомление меняются транзакционно.
