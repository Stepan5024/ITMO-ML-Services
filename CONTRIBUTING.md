# Руководство по вкладу в проект ML Classifier

Спасибо за интерес к нашему проекту! Этот документ содержит рекомендации о том, как внести вклад в разработку ML Classifier Service.

## Настройка окружения разработки

### Предварительные требования
- Python 3.12+
- Docker и Docker Compose
- Poetry (для управления зависимостями)

### Локальная настройка
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-organization/ITMO-ML-Services.git
   cd ITMO-ML-Services
   ```

2. Установите зависимости с помощью Poetry:
   ```bash
   poetry install
   ```

3. Настройте pre-commit хуки:
   ```bash
   poetry run pre-commit install
   ```

4. Создайте файл `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Запустите проект с помощью Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Процесс разработки

### Ветвление

Используйте следующие префиксы для веток:
- `feature/` - для новых функций
- `bugfix/` - для исправления ошибок
- `refactor/` - для рефакторинга кода
- `docs/` - для изменений в документации
- `test/` - для добавления или изменения тестов

Пример: `feature/add-sentiment-analysis`

### Коммиты

Следуйте соглашению [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - добавление новой функциональности
- `fix:` - исправление ошибок
- `docs:` - изменения в документации
- `style:` - форматирование, отсутствующие точки с запятой и т.д.
- `refactor:` - рефакторинг кода
- `test:` - добавление тестов
- `chore:` - обновления сборки, управление зависимостями

Пример: `feat: add text preprocessing module`

### Стиль кода

- Следуйте стилю [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Используйте типизацию
- Максимальная длина строки: 88 символов (настроено в Black)
- Для форматирования используется Black
- Для сортировки импортов используется isort
- Для линтинга используется flake8

### Pull Request (PR)

1. Обновите ветку main:
   ```bash
   git checkout main
   git pull origin main
   ```

2. Создайте новую ветку:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Внесите изменения и выполните коммит:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

4. Отправьте изменения в репозиторий:
   ```bash
   git push origin feature/your-feature-name
   ```

5. Создайте Pull Request в GitHub

6. Дождитесь прохождения CI проверок и code review

### Обновление CHANGELOG.md

При внесении существенных изменений не забудьте обновить CHANGELOG.md.
Добавьте запись в раздел "Unreleased".

## Тестирование

### Запуск тестов

```bash
poetry run pytest
```

### Проверка покрытия кода тестами

```bash
poetry run pytest --cov=ml_classifier tests/
```

## Документация

### Локальная документация API

После запуска сервиса документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Улучшение документации API

Используйте docstrings и аннотации типов для автоматической генерации документации.

Пример:
```python
@app.post("/api/v1/classify", response_model=ClassificationResult)
async def classify_text(request: ClassificationRequest) -> ClassificationResult:
    """
    Классифицирует текстовый отзыв.

    Args:
        request: Запрос на классификацию с текстом отзыва.

    Returns:
        Результат классификации с классом и вероятностью.

    Raises:
        HTTPException: Если текст пустой или слишком длинный.
    """
    # Реализация...
```

## Сообщение о проблемах

Если вы обнаружили проблему, создайте issue в репозитории, включая:
- Подробное описание проблемы
- Шаги для воспроизведения
- Ожидаемое и фактическое поведение
- Скриншоты, если применимо
- Версия ОС/браузера/Python

## Предложения по улучшению

Для предложений по улучшению:
1. Создайте issue с меткой "enhancement"
2. Опишите предлагаемую функциональность
3. Обсудите с командой
4. При одобрении, следуйте процессу PR

## Лицензия

Внося вклад в проект, вы соглашаетесь с лицензией проекта.
