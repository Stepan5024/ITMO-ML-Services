# ITMO-ML-Services/streamlit/utils/api.py
import requests
from loguru import logger
import streamlit as st

from .config import API_URL, TOKEN_SESSION_KEY


def get_headers():
    """Получить заголовки с токеном авторизации."""
    token = st.session_state.get(TOKEN_SESSION_KEY)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    # Логируем только наличие токена, но не сам токен в заголовках для безопасности
    has_token = "Bearer token" if token else "No token"
    logger.debug(f"Сформированы заголовки: {has_token}")
    return headers


def login(email, password):
    """Вход в сервис ML."""
    logger.info(f"Попытка входа для пользователя: {email}")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        if response.ok:
            data = response.json()
            if "access_token" in data:
                token = data["access_token"]
                logger.success(
                    f"Успешный вход для пользователя: {email}. Токен получен: {token[:10]}..."
                )
                # Сохраняем токен в сессии здесь не нужно, это делается в auth.py
                return data
            else:
                logger.warning(
                    f"Токен отсутствует в ответе API при успешном входе: {data}"
                )
                return None
        else:
            logger.warning(f"Ошибка входа: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при входе пользователя {email}: {str(e)}")
        return None


def register(email, password, full_name):
    """Регистрация нового пользователя."""
    logger.info(f"Попытка регистрации пользователя: {email}")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        if response.ok:
            logger.success(f"Пользователь зарегистрирован: {email}")
            return response.json()
        else:
            logger.warning(
                f"Ошибка регистрации: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        logger.exception(f"Исключение при регистрации пользователя {email}: {str(e)}")
        return None


def get_user_info():
    """Получить информацию о текущем пользователе."""
    logger.info("Запрос информации о текущем пользователе")
    try:
        headers = get_headers()
        if not headers.get("Authorization"):
            logger.error(
                "Невозможно получить информацию о пользователе: токен отсутствует"
            )
            return None

        response = requests.get(f"{API_URL}/api/v1/auth/me", headers=headers)
        if response.ok:
            user_data = response.json()
            logger.success(
                f"Информация о пользователе получена: {user_data.get('email', 'неизвестен')}"
            )
            return user_data
        else:
            logger.warning(
                f"Ошибка получения информации: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при получении информации о пользователе: {str(e)}"
        )
        return None


def get_available_models():
    """Получить список доступных моделей классификации."""
    logger.info("Запрос списка доступных моделей")
    try:
        response = requests.get(f"{API_URL}/api/v1/models", headers=get_headers())
        if response.ok:
            logger.success("Список моделей успешно получен")
            return response.json()
        else:
            logger.warning(f"Ошибка получения моделей: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при получении моделей: {str(e)}")
        return None


def classify_text(text, model_id=None, async_execution=False):
    """Классификация текста."""
    logger.info(
        f"Запрос классификации текста. Модель: {model_id}, Асинхронно: {async_execution}"
    )
    try:
        payload = {
            "text": text,
            "model_id": model_id,
            "async_execution": async_execution,
        }
        response = requests.post(
            f"{API_URL}/api/v1/classify", json=payload, headers=get_headers()
        )
        if response.ok:
            logger.success("Классификация выполнена успешно")
            return response.json()
        else:
            logger.warning(f"Ошибка классификации: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при классификации текста: {str(e)}")
        return None


def batch_classify(texts, model_id=None):
    """Классификация набора текстов."""
    logger.info(f"Запрос пакетной классификации. Кол-во текстов: {len(texts)}")
    try:
        payload = {"texts": texts, "model_id": model_id, "async_execution": True}
        response = requests.post(
            f"{API_URL}/api/v1/classify-batch", json=payload, headers=get_headers()
        )
        if response.ok:
            logger.success("Пакетная классификация завершена успешно")
            return response.json()
        else:
            logger.warning(f"Ошибка пакетной классификации: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при пакетной классификации: {str(e)}")
        return None


def get_task_status(task_id):
    """Получить статус асинхронной задачи."""
    logger.info(f"Проверка статуса задачи: {task_id}")
    try:
        response = requests.get(
            f"{API_URL}/api/v1/tasks/{task_id}", headers=get_headers()
        )
        if response.ok:
            logger.success(f"Статус задачи {task_id} успешно получен")
            return response.json()
        else:
            logger.warning(
                f"Ошибка получения статуса задачи {task_id}: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(f"Исключение при получении статуса задачи {task_id}: {str(e)}")
        return None


def get_user_tasks(page=1, size=10):
    """Получить список задач пользователя."""
    logger.info(f"Запрос задач пользователя. Страница: {page}, Размер: {size}")
    try:
        response = requests.get(
            f"{API_URL}/api/v1/tasks/?page={page}&size={size}", headers=get_headers()
        )
        if response.ok:
            logger.success("Список задач получен")
            return response.json()
        else:
            logger.warning(f"Ошибка получения задач: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при получении задач пользователя: {str(e)}")
        return None


def get_user_balance():
    """Получить баланс пользователя."""
    logger.info("Запрос баланса пользователя")
    try:
        response = requests.get(
            f"{API_URL}/api/v1/billing/balance", headers=get_headers()
        )
        if response.ok:
            logger.success("Баланс пользователя получен")
            return response.json()
        else:
            logger.warning(f"Ошибка получения баланса: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при получении баланса: {str(e)}")
        return None


def add_funds(amount):
    """Пополнить баланс пользователя."""
    logger.info(f"Попытка пополнения баланса на сумму: {amount}")
    try:
        payload = {"amount": amount}
        response = requests.post(
            f"{API_URL}/api/v1/billing/deposit", json=payload, headers=get_headers()
        )
        if response.ok:
            logger.success(f"Баланс успешно пополнен на {amount}")
            return response.json()
        else:
            logger.warning(f"Ошибка пополнения баланса: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при пополнении баланса: {str(e)}")
        return None


# Admin functions for model management


def admin_list_models(search=None, model_type=None, is_active=None, page=1, size=10):
    """Get list of all models for admin."""
    logger.info("Запрос списка моделей для администратора")
    try:
        params = {
            "search": search,
            "model_type": model_type,
            "is_active": is_active,
            "page": page,
            "size": size,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        response = requests.get(
            f"{API_URL}/api/v1/admin/models", params=params, headers=get_headers()
        )

        if response.ok:
            logger.success("Список моделей для администратора успешно получен")
            return response.json()
        else:
            logger.warning(
                f"Ошибка получения списка моделей для администратора: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при получении списка моделей для администратора: {str(e)}"
        )
        return None


def admin_get_model(model_id):
    """Get model details for admin."""
    logger.info(f"Запрос детальной информации о модели: {model_id}")
    try:
        response = requests.get(
            f"{API_URL}/api/v1/admin/models/{model_id}", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Детальная информация о модели {model_id} успешно получена")
            return response.json()
        else:
            logger.warning(
                f"Ошибка получения информации о модели: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при получении информации о модели {model_id}: {str(e)}"
        )
        return None


def admin_create_model(model_data):
    """Create new model as admin."""
    logger.info(f"Создание новой модели: {model_data.get('name', 'unnamed')}")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/admin/models", json=model_data, headers=get_headers()
        )

        if response.ok:
            logger.success("Модель успешно создана")
            return response.json()
        else:
            logger.warning(
                f"Ошибка создания модели: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        logger.exception(f"Исключение при создании модели: {str(e)}")
        return None


def admin_update_model(model_id, model_data):
    """Update existing model as admin."""
    logger.info(f"Обновление модели {model_id}")
    try:
        response = requests.put(
            f"{API_URL}/api/v1/admin/models/{model_id}",
            json=model_data,
            headers=get_headers(),
        )

        if response.ok:
            logger.success(f"Модель {model_id} успешно обновлена")
            return response.json()
        else:
            logger.warning(
                f"Ошибка обновления модели: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        logger.exception(f"Исключение при обновлении модели {model_id}: {str(e)}")
        return None


def admin_delete_model(model_id):
    """Delete model as admin."""
    logger.info(f"Удаление модели {model_id}")
    try:
        response = requests.delete(
            f"{API_URL}/api/v1/admin/models/{model_id}", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Модель {model_id} успешно удалена")
            return True
        else:
            logger.warning(f"Ошибка удаления модели: {response.status_code}")
            return False
    except Exception as e:
        logger.exception(f"Исключение при удалении модели {model_id}: {str(e)}")
        return False


def admin_activate_model(model_id):
    """Activate model as admin."""
    logger.info(f"Активация модели {model_id}")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/admin/models/{model_id}/activate", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Модель {model_id} успешно активирована")
            return response.json()
        else:
            logger.warning(f"Ошибка активации модели: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при активации модели {model_id}: {str(e)}")
        return None


def admin_deactivate_model(model_id):
    """Deactivate model as admin."""
    logger.info(f"Деактивация модели {model_id}")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/admin/models/{model_id}/deactivate",
            headers=get_headers(),
        )

        if response.ok:
            logger.success(f"Модель {model_id} успешно деактивирована")
            return response.json()
        else:
            logger.warning(f"Ошибка деактивации модели: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при деактивации модели {model_id}: {str(e)}")
        return None


def admin_upload_model_version(
    model_id,
    version,
    model_file,
    vectorizer_file=None,
    metrics="{}",
    parameters="{}",
    status="TRAINED",
):
    """Upload new model version as admin."""
    logger.info(f"Загрузка новой версии модели {model_id}, версия: {version}")
    try:
        files = {
            "model_file": model_file,
            "version": (None, version),
            "metrics": (None, metrics),
            "parameters": (None, parameters),
            "status_value": (None, status),
        }

        if vectorizer_file:
            files["vectorizer_file"] = vectorizer_file

        response = requests.post(
            f"{API_URL}/api/v1/admin/models/{model_id}/versions",
            files=files,
            headers=get_headers(),
        )

        if response.ok:
            logger.success(f"Новая версия модели {model_id} успешно загружена")
            return response.json()
        else:
            logger.warning(
                f"Ошибка загрузки версии модели: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        logger.exception(f"Исключение при загрузке версии модели {model_id}: {str(e)}")
        return None


def admin_list_model_versions(model_id):
    """List all versions of a model as admin."""
    logger.info(f"Запрос списка версий модели {model_id}")
    try:
        response = requests.get(
            f"{API_URL}/api/v1/admin/models/{model_id}/versions", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Список версий модели {model_id} успешно получен")
            return response.json()
        else:
            logger.warning(
                f"Ошибка получения списка версий модели: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при получении списка версий модели {model_id}: {str(e)}"
        )
        return None


def admin_get_version(version_id):
    """Get model version details as admin."""
    logger.info(f"Запрос информации о версии модели {version_id}")
    try:
        response = requests.get(
            f"{API_URL}/api/v1/admin/versions/{version_id}", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Информация о версии модели {version_id} успешно получена")
            return response.json()
        else:
            logger.warning(
                f"Ошибка получения информации о версии модели: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при получении информации о версии модели {version_id}: {str(e)}"
        )
        return None


def admin_delete_version(version_id):
    """Delete model version as admin."""
    logger.info(f"Удаление версии модели {version_id}")
    try:
        response = requests.delete(
            f"{API_URL}/api/v1/admin/versions/{version_id}", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Версия модели {version_id} успешно удалена")
            return True
        else:
            logger.warning(f"Ошибка удаления версии модели: {response.status_code}")
            return False
    except Exception as e:
        logger.exception(
            f"Исключение при удалении версии модели {version_id}: {str(e)}"
        )
        return False


def admin_set_default_version(version_id):
    """Set model version as default."""
    logger.info(f"Установка версии модели {version_id} по умолчанию")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/admin/versions/{version_id}/set-default",
            headers=get_headers(),
        )

        if response.ok:
            logger.success(
                f"Версия модели {version_id} успешно установлена по умолчанию"
            )
            return response.json()
        else:
            logger.warning(
                f"Ошибка установки версии по умолчанию: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при установке версии по умолчанию {version_id}: {str(e)}"
        )
        return None


# Admin functions for user management


def admin_list_users(search=None, is_active=None, is_admin=None, page=1, size=10):
    """Get list of users for admin."""
    logger.info("Запрос списка пользователей для администратора")
    try:
        params = {
            "search": search,
            "is_active": is_active,
            "is_admin": is_admin,
            "page": page,
            "size": size,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        response = requests.get(
            f"{API_URL}/api/v1/admin/users", params=params, headers=get_headers()
        )

        if response.ok:
            logger.success("Список пользователей для администратора успешно получен")
            return response.json()
        else:
            logger.warning(
                f"Ошибка получения списка пользователей: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(f"Исключение при получении списка пользователей: {str(e)}")
        return None


def admin_get_user(user_id):
    """Get user details for admin."""
    logger.info(f"Запрос информации о пользователе {user_id}")
    try:
        response = requests.get(
            f"{API_URL}/api/v1/admin/users/{user_id}", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Информация о пользователе {user_id} успешно получена")
            return response.json()
        else:
            logger.warning(
                f"Ошибка получения информации о пользователе: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при получении информации о пользователе {user_id}: {str(e)}"
        )
        return None


def admin_activate_user(user_id):
    """Activate user account as admin."""
    logger.info(f"Активация пользователя {user_id}")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/admin/users/{user_id}/activate", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Пользователь {user_id} успешно активирован")
            return response.json()
        else:
            logger.warning(f"Ошибка активации пользователя: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при активации пользователя {user_id}: {str(e)}")
        return None


def admin_deactivate_user(user_id):
    """Deactivate user account as admin."""
    logger.info(f"Деактивация пользователя {user_id}")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/admin/users/{user_id}/deactivate", headers=get_headers()
        )

        if response.ok:
            logger.success(f"Пользователь {user_id} успешно деактивирован")
            return response.json()
        else:
            logger.warning(f"Ошибка деактивации пользователя: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Исключение при деактивации пользователя {user_id}: {str(e)}")
        return None


def admin_set_admin_status(user_id, is_admin):
    """Set admin status for user."""
    logger.info(
        f"Установка статуса администратора для пользователя {user_id}: {is_admin}"
    )
    try:
        response = requests.post(
            f"{API_URL}/api/v1/admin/users/{user_id}/admin-status",
            json={"is_admin": is_admin},
            headers=get_headers(),
        )

        if response.ok:
            logger.success(
                f"Статус администратора для пользователя {user_id} успешно установлен"
            )
            return response.json()
        else:
            logger.warning(
                f"Ошибка установки статуса администратора: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.exception(
            f"Исключение при установке статуса администратора для пользователя {user_id}: {str(e)}"
        )
        return None
