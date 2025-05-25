# 🎉 Birthday Reminder Bot

[![Python](https://img.shields.io/badge/Python-3.13%2B-green?logo=python)](https://www.python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://core.telegram.org/bots)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue?logo=docker)](https://www.docker.com/)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/evgensetrov/birthday-reminder/ci.yml?label=CI\&logo=github)](https://github.com/evgensetrov/birthday-reminder/actions)
[![Last Commit](https://img.shields.io/github/last-commit/evgensetrov/birthday-reminder/main)](https://github.com/evgensetrov/birthday-reminder)

**Birthday Reminder Bot** — это Telegram-бот, который помогает вам не забывать о днях рождения ваших друзей и близких. Он отправляет уведомления в день рождения и за несколько дней до него, чтобы вы могли подготовиться заранее.

## 🚀 Возможности

* 📅 Добавление дней рождения с указанием имени и даты
* 🔔 Уведомления в день рождения, за день и за неделю.
* 📝 Управление списком дней рождения (добавление, удаление, просмотр)
* 🐳 Поддержка Docker для легкого развертывания
* ⚙️ Автоматизация с помощью GitHub Actions

## 🛠️ Технологии

* **Проверено на Python 3.13+ (возможно будет работать на 3.10+)**
* **aiogram**
* **PostgreSQL**
* **Docker**
* **GitHub Actions**

## 📦 Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/evgensetrov/birthday-reminder.git
cd birthday-reminder
```

### 2. Настройка .env

Создайте файл `.env` на основе `.env.example`:
```
cp .env.example .env
```

Заполните переменные:
* **TELEGRAM_BOT_TOKEN** - токен для Telegram-бота;
* **POSTGRES_INIT_PATH** - путь с ```.sql```- или ```.sh```-файлами для инициализации БД;
* **POSTGRES_DATA_PATH** - путь для хранения файлов БД.

Остальные поля можно оставить по умолчанию.

### 3. Установка docker:

Подробно описано, например, [здесь](https://docs.docker.com/engine/install/)

### 4. Сборка и запуск контейнеров:

```
docker compose -f docker-compose-dev.yml up -d --build
```

### 5. Обновление:
```
git fetch
docker compose -f docker-compose-dev.yml up -d --build
```