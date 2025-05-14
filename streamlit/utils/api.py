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
