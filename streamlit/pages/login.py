# ITMO-ML-Services/streamlit/pages/login.py
import streamlit as st
from loguru import logger

from utils.auth import login
from utils.api import register

st.set_page_config(
    page_title="Login - ML Classification", page_icon="🔑", layout="centered"
)

logger.debug("Страница входа загружена.")
st.title("Login")

# Tabs for login and registration
tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    logger.debug("Открыта вкладка входа.")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log In")

    if submit:
        logger.info(f"Нажата кнопка входа. Email: {email}")
        if email and password:
            with st.spinner("Logging in..."):
                logger.debug("Попытка входа пользователя через API...")
                if login(email, password):
                    logger.success(f"Пользователь {email} успешно вошёл в систему.")
                    st.success("Login successful!")
                    st.switch_page("app.py")
                else:
                    logger.warning(f"Неудачная попытка входа для пользователя: {email}")
                    st.error("Invalid credentials. Please try again.")
        else:
            logger.warning("Одно или оба поля (email, пароль) не заполнены.")
            st.warning("Please enter both email and password.")

with tab2:
    logger.debug("Открыта вкладка регистрации.")
    with st.form("register_form"):
        new_email = st.text_input("Email")
        new_full_name = st.text_input("Full Name")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        register_button = st.form_submit_button("Register")

    if register_button:
        logger.info(f"Нажата кнопка регистрации. Email: {new_email}")
        if new_email and new_full_name and new_password:
            if new_password != confirm_password:
                logger.warning("Пароли не совпадают при регистрации.")
                st.error("Passwords do not match!")
            else:
                with st.spinner("Registering..."):
                    logger.debug("Отправка данных на регистрацию через API...")
                    result = register(new_email, new_password, new_full_name)
                    if result:
                        logger.success(
                            f"Пользователь {new_email} успешно зарегистрирован."
                        )
                        st.success("Registration successful! Please log in.")
                    else:
                        logger.error(f"Ошибка регистрации пользователя: {new_email}")
                        st.error(
                            "Registration failed. Please try a different email or check your connection."
                        )
        else:
            logger.warning("Не все поля регистрации заполнены.")
            st.warning("Please fill out all fields.")
