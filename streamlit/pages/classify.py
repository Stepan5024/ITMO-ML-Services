# ITMO-ML-Services/streamlit/pages/classify.py
import streamlit as st
from loguru import logger

from utils.auth import check_login
from utils.api import classify_text, get_available_models

# Проверка статуса входа
logger.debug("Проверка авторизации пользователя...")
check_login()
logger.debug("Авторизация подтверждена.")

st.set_page_config(page_title="Text Classification", page_icon="📝", layout="wide")

logger.info("Страница классификации текста загружена.")
st.title("Text Classification")
st.write("Submit text to classify using our machine learning models.")

# Получение доступных моделей
logger.debug("Получение списка доступных моделей...")
models = get_available_models()
model_options = {}

if models and "items" in models:
    model_options = {
        f"{model['name']} - {model['model_type']}": model["id"]
        for model in models["items"]
    }
    model_options["Default Model"] = None
    logger.info(f"Доступные модели: {list(model_options.keys())}")
else:
    model_options["Default Model"] = None
    logger.warning("Список моделей недоступен или пуст.")

# Форма классификации
with st.form("classification_form"):
    text = st.text_area("Enter text to classify:", height=200)

    col1, col2 = st.columns(2)
    with col1:
        model_name = st.selectbox("Select model:", list(model_options.keys()))
    with col2:
        async_execution = st.checkbox(
            "Asynchronous execution", help="Process in the background for longer texts"
        )

    submit = st.form_submit_button("Submit for Classification")

if submit:
    logger.info("Пользователь отправил форму классификации.")
    if not text:
        logger.warning("Текст для классификации не был введён.")
    else:
        model_id = model_options[model_name]
        logger.debug(
            f"Выполнение классификации. Модель: {model_name}, Async: {async_execution}"
        )

        with st.spinner("Processing..."):
            result = classify_text(text, model_id, async_execution)

            if result:
                logger.success("Классификация выполнена успешно.")
                st.success("Classification complete!")

                if async_execution and "task_id" in result:
                    task_id = result["task_id"]
                    logger.info(f"Асинхронная задача отправлена. Task ID: {task_id}")
                    st.info(f"Task submitted successfully! Task ID: {task_id}")
                    st.info("You can check the result in the History tab.")
                else:
                    st.subheader("Results:")
                    logger.debug("Отображение результатов классификации...")

                    col1, col2 = st.columns(2)

                    with col1:
                        if "prediction" in result:
                            st.metric("Sentiment", result["prediction"])
                            logger.debug(f"Prediction: {result['prediction']}")

                        if "confidence" in result:
                            st.metric("Confidence", f"{result['confidence']:.2%}")
                            logger.debug(f"Confidence: {result['confidence']}")

                    with col2:
                        if "execution_time_ms" in result:
                            st.metric(
                                "Processing Time", f"{result['execution_time_ms']} ms"
                            )
                            logger.debug(
                                f"Execution Time: {result['execution_time_ms']} ms"
                            )

                        if "categories" in result and result["categories"]:
                            st.write("**Categories:**")
                            for category in result["categories"]:
                                st.write(f"- {category.capitalize()}")
                            logger.debug(
                                f"Categories: {', '.join(result['categories'])}"
                            )

                    with st.expander("View raw JSON result"):
                        st.json(result)
                        logger.debug("Отображение сырых данных JSON результата.")
            else:
                logger.error("Ошибка при выполнении классификации.")
                st.error(
                    "Classification failed. Please try again or check your balance."
                )
