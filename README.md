# ITMO-ML-Services

# ML Classifier Service

Сервис машинного обучения для классификации отзывов студентов с использованием FastAPI, Celery, PostgreSQL и Redis.

## Требования

- Docker и Docker Compose
- Git
-
## Project Structure

## Getting Started

### Poetry Setup

This project uses [Poetry](https://python-poetry.org/) for dependency management.

#### 1. Install Poetry

Follow the official installation instructions:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add Poetry to your PATH (you may want to add this to your shell profile):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify installation:
```bash
poetry --version
```

#### 2. Install Dependencies

Clone the repository and navigate to the project directory:
```bash
git clone https://github.com/yourusername/ITMO-ML-Services.git
cd ITMO-ML-Services
```

Install dependencies:
```bash
poetry install
```

#### 3. Activate Virtual Environment

```bash
poetry shell
```

Or run commands directly:
```bash
poetry run python your_script.py
```

### Running Tests

Run tests using pytest:
```bash
poetry run pytest
```

### Code Quality

Format code:
```bash
poetry run black .
poetry run isort .
```

Check code quality:
```bash
poetry run flake8
```
```



## Быстрый старт с Docker

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-organization/ITMO-ML-Services.git
cd ITMO-ML-Services
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# Создайте и отредактируйте файл .env
touch .env

# Добавьте следующие переменные окружения
echo "POSTGRES_USER=mluser" >> .env
echo "POSTGRES_PASSWORD=securepassword" >> .env
echo "POSTGRES_DB=ml_classifier" >> .env
echo "ENVIRONMENT=development" >> .env
```

### 3. Сборка и запуск контейнеров

```bash
# Сборка и запуск всех сервисов
docker-compose up --build

# Или запуск в фоновом режиме
docker-compose up -d --build
```

### 4. Проверка работы сервиса

Проверьте работу API по адресу: [http://localhost:8000](http://localhost:8000)

Документация API доступна по адресу: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Остановка контейнеров

```bash
docker-compose down
```

## Использование отдельных сервисов

### Запуск только API сервиса

```bash
docker-compose up app
```

### Запуск только Celery workers

```bash
docker-compose up celery
```

## Структура проекта

```
ITMO-ML-Services/
├── src/
│   └── ml_classifier/       # Основной пакет приложения
│       ├── data/            # Модули для обработки данных
│       ├── models/          # ML модели и схемы Pydantic
│       ├── services/        # Бизнес-логика
│       ├── utils/           # Утилиты и вспомогательные функции
│       ├── __init__.py      # Инициализация пакета
│       ├── main.py          # Основная точка входа FastAPI приложения
│       └── tasks.py         # Задачи Celery
├── docker-compose.yml       # Конфигурация Docker Compose
├── Dockerfile               # Инструкция сборки Docker образа
├── pyproject.toml           # Конфигурация Poetry и зависимостей
├── poetry.lock              # Фиксированные версии зависимостей
└── README.md                # Документация проекта
```

## Разработка

### Локальная разработка с Docker

При локальной разработке можно использовать режим горячей перезагрузки:

```bash
docker-compose up
```

Файлы исходного кода подключены через volume, поэтому изменения в коде будут автоматически применяться.

### Полезные команды Docker

```bash
# Просмотр логов определенного сервиса
docker-compose logs app
docker-compose logs celery

# Выполнение команд внутри контейнера
docker-compose exec app bash

# Перезапуск одного сервиса
docker-compose restart app
```

## API Endpoints

- `GET /` - Корневой эндпоинт с приветственным сообщением
- `GET /health` - Проверка состояния сервиса

## Устранение неполадок

### Проблемы с подключением к базе данных
Проверьте переменные окружения в `.env` файле и доступность сервиса PostgreSQL:

```bash
docker-compose ps postgres
```

### Проблемы с Celery или Redis
Проверьте доступность Redis сервера:

```bash
docker-compose ps redis
docker-compose logs redis
```
