# ITMO-ML-Services/streamlit/app.py
from loguru import logger

import streamlit as st
from utils.auth import check_login, logout

logger.info("Инициализация главной страницы приложения")

st.set_page_config(
    page_title="ML Classification Service",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

logger.debug("Проверка статуса авторизации пользователя...")
try:
    authenticated = check_login()
    if not authenticated:
        logger.warning("Пользователь не авторизован, перенаправление на страницу входа")
        st.switch_page("pages/login.py")
    logger.debug("Авторизация подтверждена, пользователь имеет валидный токен")
except Exception as e:
    logger.warning(f"Ошибка при проверке авторизации: {e}")
    st.switch_page("pages/login.py")

# Display sidebar with navigation
st.sidebar.title("ML Classification")

# Get user info
user_info = st.session_state.get("user_info", {})
logger.debug(
    f"Информация о пользователе из сессии: {user_info.get('email', 'не найдена')}"
)
if user_info:
    st.sidebar.write(
        f"Welcome, {user_info.get('full_name', user_info.get('email', 'User'))}"
    )

# Navigation
pages = {
    "Text Classification": "pages/classify.py",
    "Batch Processing": "pages/batch.py",
    "History": "pages/history.py",
    "Balance": "pages/balance.py",
}

for page_name, page_path in pages.items():
    st.sidebar.page_link(page_path, label=page_name)

if st.sidebar.button("Logout"):
    logger.info("Пользователь нажал кнопку выхода")
    logout()
    logger.debug("Выполнен выход из системы, перенаправление на страницу входа")
    st.switch_page("pages/login.py")

# Main content
st.title("ML Classification Service")
st.write("Welcome to the ML Classification Service interface!")
st.write(
    "Use the sidebar to navigate to different features or get started with text classification below."
)

# Quick classification form
st.header("Quick Classification")
with st.form("quick_classify"):
    text = st.text_area("Enter text to classify:", height=150)
    submit = st.form_submit_button("Classify")

if submit:
    logger.info("Пользователь отправил форму быстрой классификации")
    if not text:
        logger.warning("Текст для классификации не был введён")
        st.warning("Please enter text to classify")
    else:
        logger.debug("Выполнение быстрой классификации текста")
        with st.spinner("Classifying..."):
            from utils.api import classify_text

            result = classify_text(text)

            if result:
                logger.success("Быстрая классификация выполнена успешно")
                st.success("Classification complete!")

                # Display result in a better format
                col1, col2 = st.columns(2)

                with col1:
                    if "prediction" in result:
                        st.metric("Sentiment", result["prediction"])

                    if "confidence" in result:
                        st.metric("Confidence", f"{result['confidence']:.2%}")

                with col2:
                    if "execution_time_ms" in result:
                        st.metric(
                            "Processing Time", f"{result['execution_time_ms']} ms"
                        )

                    if "categories" in result and result["categories"]:
                        st.write("**Categories:**")
                        for category in result["categories"]:
                            st.write(f"- {category.capitalize()}")

                # Show raw JSON for advanced users
                with st.expander("View raw JSON result"):
                    st.json(result)
            else:
                logger.error("Ошибка при выполнении классификации")
                st.error(
                    "Classification failed. Please try again or check your balance."
                )
