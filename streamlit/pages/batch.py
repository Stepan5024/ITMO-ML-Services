# ITMO-ML-Services/streamlit/pages/batch.py
import streamlit as st
import pandas as pd
from loguru import logger
from utils.auth import check_login
from utils.api import batch_classify, get_available_models

# Проверка статуса входа
logger.debug("Проверка авторизации пользователя...")
check_login()
logger.debug("Авторизация подтверждена.")

st.set_page_config(page_title="Batch Classification", page_icon="📊", layout="wide")

logger.info("Страница пакетной классификации загружена.")
st.title("Batch Text Classification")
st.write("Submit multiple texts for classification in a single batch.")

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

# Input methods tabs
logger.debug("Инициализация вкладок для ввода данных...")
tab1, tab2 = st.tabs(["Text Input", "CSV Upload"])

texts_to_classify = []

with tab1:
    st.subheader("Enter Texts")

    # Dynamic form for multiple text inputs
    num_texts = st.number_input("Number of texts", min_value=1, max_value=20, value=3)

    with st.form("multi_text_form"):
        text_inputs = []

        for i in range(num_texts):
            text = st.text_area(f"Text {i + 1}", key=f"text_{i}")
            text_inputs.append(text)

        model_name = st.selectbox(
            "Select model:", list(model_options.keys()), key="model_select_1"
        )
        submit_texts = st.form_submit_button("Submit Batch")

    if submit_texts:
        logger.info("Пользователь отправил форму для классификации текстов.")
        # Filter out empty texts
        texts_to_classify = [text for text in text_inputs if text.strip()]
        if not texts_to_classify:
            logger.warning("Пользователь не ввел тексты для классификации.")
            st.warning("Please enter at least one text to classify.")

with tab2:
    st.subheader("Upload CSV File")
    st.write(
        "Upload a CSV file with one text per row. The first column will be used for classification."
    )

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        try:
            # Read the CSV file
            csv_data = pd.read_csv(uploaded_file)

            if len(csv_data.columns) == 0:
                st.error("The CSV file appears to be empty.")
            else:
                # Display preview
                st.write("Preview:")
                st.dataframe(csv_data.head(5))

                # Get column selection
                text_column = st.selectbox(
                    "Select column containing texts:", csv_data.columns
                )

                with st.form("csv_form"):
                    model_name_csv = st.selectbox(
                        "Select model:",
                        list(model_options.keys()),
                        key="model_select_2",
                    )
                    submit_csv = st.form_submit_button("Submit Batch")

                if submit_csv:
                    logger.info(
                        f"Пользователь отправил CSV файл для классификации, колонка: {text_column}"
                    )
                    # Get texts from the selected column
                    texts_to_classify = csv_data[text_column].dropna().tolist()

                    if not texts_to_classify:
                        logger.warning(
                            f"Не найдено текстов для классификации в колонке {text_column}"
                        )
                        st.warning("No valid texts found in the selected column.")

        except Exception as e:
            logger.error(f"Ошибка обработки CSV файла: {str(e)}")
            st.error(f"Error processing CSV file: {str(e)}")

# Process batch if texts are ready
if texts_to_classify:
    # Get model ID from selection
    if "model_name_csv" in locals() and submit_csv:
        model_id = model_options[model_name_csv]
    else:
        model_id = model_options[model_name]

    logger.info(
        f"Отправка пакета с {len(texts_to_classify)} текстами. Модель: {model_id}"
    )
    # Display batch info
    st.write(f"Submitting batch with {len(texts_to_classify)} text(s)...")

    with st.spinner("Processing batch..."):
        logger.debug("Выполнение пакетной классификации...")
        result = batch_classify(texts_to_classify, model_id)

        if result and "task_id" in result:
            task_id = result["task_id"]
            logger.success(f"Пакет отправлен успешно. Task ID: {task_id}")
            st.success("Batch submitted successfully!")
            st.info(f"Task ID: {task_id}")
            st.info(
                "You can check the results in the History tab once processing is complete."
            )

            # Display estimated completion time if available
            if "estimated_completion_time" in result:
                estimated_time = result["estimated_completion_time"]
                logger.info(f"Ожидаемое время завершения: {estimated_time}")
                st.info(f"Estimated completion time: {estimated_time}")

            # Add button to check history
            if st.button("Go to History"):
                logger.debug("Пользователь переходит на страницу истории.")
                st.switch_page("pages/history.py")

        else:
            logger.error("Ошибка при отправке пакета на классификацию.")
            st.error(
                "Batch submission failed. Please check your connection or balance."
            )
