# ITMO-ML-Services/streamlit/utils/auth.py
import streamlit as st
from loguru import logger

from .config import TOKEN_SESSION_KEY, USER_SESSION_KEY
from .api import login as api_login, get_user_info


def check_login():
    """Check if user is logged in and redirect if not."""
    logger.debug(
        f"Проверка наличия токена в сессии... Ключи сессии: {list(st.session_state.keys())}"
    )
    if TOKEN_SESSION_KEY not in st.session_state:
        logger.warning("Токен не найден в сессии. Перенаправление на страницу входа.")
        st.switch_page("pages/login.py")
        return False

    token = st.session_state.get(TOKEN_SESSION_KEY)
    logger.debug(f"Найден токен: {token[:10]}..." if token else "Токен пустой")

    logger.debug("Проверка наличия информации о пользователе в сессии...")
    if USER_SESSION_KEY not in st.session_state:
        logger.info("Информация о пользователе отсутствует. Запрос к API.")
        user_info = get_user_info()
        if user_info:
            logger.success(
                f"Информация о пользователе получена: {user_info.get('email', 'неизвестен')}"
            )
            st.session_state[USER_SESSION_KEY] = user_info
        else:
            logger.warning(
                "Не удалось получить информацию о пользователе. Возможно, токен истек."
            )
            st.session_state.pop(TOKEN_SESSION_KEY, None)
            st.switch_page("pages/login.py")
            return False

    return True


def login(email, password):
    """Log in user and store token in session."""
    logger.info(f"Попытка входа пользователя: {email}")
    response = api_login(email, password)

    if not response:
        logger.error(f"Ответ API пустой при входе пользователя: {email}")
        return False

    if "access_token" not in response:
        logger.error(f"Токен отсутствует в ответе API: {response}")
        return False

    # Сохраняем токен в сессии
    token = response["access_token"]
    logger.success(
        f"Вход успешен для пользователя: {email}. Токен получен: {token[:10]}..."
    )
    st.session_state[TOKEN_SESSION_KEY] = token

    # Важный момент: синхронно проверяем, что токен действительно сохранился
    if TOKEN_SESSION_KEY not in st.session_state:
        logger.error(f"Не удалось сохранить токен в сессии для: {email}")
        return False

    logger.debug("Запрашивается информация о пользователе после входа...")
    user_info = get_user_info()
    if user_info:
        logger.success(
            f"Информация о пользователе успешно сохранена в сессии: {user_info.get('email', 'неизвестен')}"
        )
        st.session_state[USER_SESSION_KEY] = user_info
        return True
    else:
        logger.error(
            f"Не удалось получить информацию о пользователе после входа: {email}"
        )

    return True  # Возвращаем True, т.к. аутентификация прошла успешно, даже если данные пользователя не получены


def logout():
    """Log out user by clearing session state."""
    logger.info("Выход пользователя. Очистка состояния сессии.")
    # Удаляем только ключи аутентификации для безопасного выхода
    st.session_state.pop(TOKEN_SESSION_KEY, None)
    st.session_state.pop(USER_SESSION_KEY, None)
    logger.debug(f"Сессия после выхода: {list(st.session_state.keys())}")


def check_admin_access():
    """Check if user is logged in and has admin privileges."""
    logger.debug("Проверка административных прав пользователя")
    # First check if user is logged in
    if not check_login():
        return False

    # Then check if user has admin privileges
    user_info = st.session_state.get(USER_SESSION_KEY, {})
    if not user_info.get("is_admin", False):
        logger.warning(
            f"Пользователь {user_info.get('email', 'unknown')} не имеет прав администратора"
        )
        st.error("У вас нет прав администратора для доступа к этой странице")
        st.switch_page("app.py")
        return False

    logger.success(f"Пользователь {user_info.get('email')} имеет права администратора")
    return True
