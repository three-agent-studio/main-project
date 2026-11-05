# Разработка и расширение каркаса

## Языки и ответственность

Сервер — **Python 3.12+ / Django 5.2 / DRF**. Интерфейс — **TypeScript / React**, разметка JSX и CSS Modules. База — PostgreSQL 17.

- №1: `backend/config`, `backend/accounts`, `backend/core`, будущий `backend/academics`, `contracts`.
- №2: `frontend/src/app`, `frontend/src/shared`, `frontend/src/features/student`.
- №3: будущие `backend/service_requests`, `backend/notifications`, `frontend/src/features/staff`, инфраструктура и E2E.
- Общие Python-зависимости и маршруты сервера меняет №1; frontend package/lock/router — №2.
- Миграции принадлежат Django-приложению; не редактировать чужие уже применённые миграции.

План: https://github.com/three-agent-studio/main-project/issues/2. Эта основа относится к #3/#4 и частично #5.
Не добавлены фиктивные API расписания/заявок: реальные модули подключаются по мере выполнения Issues.

## Первый запуск

Требуются Python 3.12+, Node 22.13+, npm и Docker Compose (либо установленный PostgreSQL).
Из корня репозитория:

```sh
cp .env.example .env
# Заполнить POSTGRES_PASSWORD в локальном .env. Файл содержит только shell-совместимые значения.
docker compose up -d db
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
set -a
. ./.env
set +a
cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Во втором терминале:

```sh
cd frontend
npm ci
npm run dev
```

Открыть `http://127.0.0.1:5173`. **Все браузерные запросы через этот origin**, включая /admin и /auth: Vite проксирует их в Django.
Через `/admin/` создать только вымышленные Faculty, StudyGroup, обычных User и StudentProfile. Не выдавать студентам is_staff/is_superuser.
Для входа студента используйте `/auth/login/`; административная учётная запись без StudentProfile допустима, интерфейс показывает соответствующее состояние.
Автоматическая генерация демонстрационных аккаунтов и ограниченный сотрудник — #5/#8.

## Проверки

```sh
cd backend
../.venv/bin/ruff check .
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/pytest
cd ../frontend
npm run lint
npm test
npm run build
```

По умолчанию pytest использует SQLite только для быстрых тестов; `TEST_POSTGRES=1` включает PostgreSQL. CI проверяет PostgreSQL, миграции, API-схему, линтеры и frontend build/tests.
Production никогда не переключается на SQLite при ошибке конфигурации.

## Как добавить раздел интерфейса

1. Создать свою папку `features/student/<feature>` или `features/staff/<feature>`.
2. Экспортировать из `index.ts` дескриптор AppModule с уникальными id/path и lazy-компонентом.
3. Подключить экспорт в `app/modules.ts`: меню и маршруты формируются из одного списка.
4. Использовать `Page`, `Card`, CSS Modules и токены `shared/styles/tokens.css`.
5. API вызывать через `shared/api/client.ts`; предусмотреть загрузку, отсутствие данных, ошибку и повтор.
6. Защищённость маршрута в UI — удобство, а не контроль доступа. Сервер обязан проверять права.

Пример публичного экспорта:

```tsx
import { lazy } from 'react';
import type { AppModule } from '../../../shared/types/module';
export const scheduleModule: AppModule = {
  id: 'schedule', path: '/schedule', label: 'Расписание',
  Component: lazy(() => import('./SchedulePage')),
};
```

Feature-модули не импортируют внутренности друг друга. Общие элементы переносить в shared только при реальном повторном использовании.
Код содержит пояснения к решениям, особенно сессиям, кешированию и расширению модулей; комментарии должны объяснять причину, а не повторять строку кода.

## Как добавить серверный модуль

Создать Django app с собственными models/serializers/views/urls/tests/migrations. Согласовать контракт и добавить app в settings, маршруты — через include.
Имя `service_requests` выбрано вместо `requests`, чтобы не затенять популярную Python HTTP-библиотеку.
Пользователь — `settings.AUTH_USER_MODEL`, не прямой импорт встроенного auth.User.
Изменение модели → новая миграция → тест на PostgreSQL. Проверять чужой доступ к спискам и отдельным объектам, а также подмену владельца при создании.

## До публичного выпуска

Каркас ещё не полный MVP. В #5 нужны ограничение попыток входа, роли сотрудника и тестовые аккаунты; в #11 — HTTPS reverse proxy, резервное копирование и проверка доступа из России.
Production: `DJANGO_SETTINGS_MODULE=config.settings.production`, длинный случайный DJANGO_SECRET_KEY, hosts, пароль БД, HTTPS CSRF origins. Запустить `check --deploy`, миграции и collectstatic отдельным шагом выпуска.
Gunicorn доступен только доверенному reverse proxy, который перезаписывает X-Forwarded-Proto. Не выставлять порт БД наружу.

## Воспроизводимые зависимости

`frontend/package-lock.json` закрепляет npm-дерево; установка — `npm ci`. `backend/constraints.txt` фиксирует Python-зависимости (включая транзитивные и тестовые), применяется из requirements.txt. Обновлять их отдельным PR и повторять CI. Не менять lock-файл вручную.

Override `minimatch: 11.0.1` закрывает GHSA-g3hv-75wg-m249 в цепочке ESLint/typescript-eslint. Совместимость проверяется линтером и тестами; убрать override после исправления диапазонов upstream и чистого npm audit.

CI выполняет 5 серверных тестов на PostgreSQL, 3 frontend unit-теста и сквозной вход/профиль/выход в Chromium на desktop и 360 px. Скриншоты сохраняются в артефакте. Это не заменяет будущую приёмку на реальных Android/iOS устройствах в #12.

Для локальных браузерных тестов нужна отдельная одноразовая БД с вымышленными данными; seed_browser.py предназначен только для такого окружения. Не запускайте seed на рабочей БД.

При подготовке основы локальная сеть не позволяла скачать пакеты; полная проверка выполнена в GitHub Actions. Для запуска у разработчика нужны установленные зависимости и PostgreSQL.
