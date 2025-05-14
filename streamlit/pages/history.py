# ITMO-ML-Services/streamlit/pages/history.py
import streamlit as st
import time
from loguru import logger
from utils.auth import check_login
from utils.api import get_user_tasks, get_task_status

# Проверка статуса входа
logger.debug("Проверка авторизации пользователя...")
check_login()
logger.debug("Авторизация подтверждена.")

st.set_page_config(page_title="Task History", page_icon="📋", layout="wide")

logger.info("Страница истории задач загружена.")
st.title("Classification History")
st.write("View and manage your classification tasks.")

# Pagination controls
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    page = st.number_input("Page", min_value=1, value=1)
with col3:
    size = st.selectbox("Items per page", [10, 20, 50, 100], index=0)

# Refresh button
refresh = st.button("Refresh", use_container_width=True)
if refresh:
    logger.info("Пользователь запросил обновление истории задач.")

# Get tasks
logger.debug(f"Получение списка задач. Страница: {page}, Размер: {size}")
tasks_response = get_user_tasks(page, size)

if tasks_response and "items" in tasks_response:
    tasks = tasks_response["items"]
    total = tasks_response.get("total", 0)

    logger.info(f"Получено {len(tasks)} из {total} задач.")
    st.write(f"Showing {len(tasks)} of {total} tasks")

    if not tasks:
        logger.info("Задачи не найдены.")
        st.info("No tasks found. Submit some classifications to see your history.")
    else:
        # Create a table view of tasks
        task_data = []
        for task in tasks:
            status_color = {
                "pending": "🟡",
                "processing": "🔵",
                "completed": "🟢",
                "failed": "🔴",
            }.get(task.get("status", "").lower(), "⚪")

            created_at = task.get("created_at", "N/A")
            completed_at = task.get("completed_at", "N/A")

            task_data.append(
                {
                    "ID": task.get("id", "N/A"),
                    "Status": f"{status_color} {task.get('status', 'N/A')}",
                    "Created": created_at,
                    "Completed": completed_at,
                    "Duration": task.get("duration", "N/A")
                    if task.get("duration")
                    else "N/A",
                }
            )

        # Convert to DataFrame for better display
        import pandas as pd

        df = pd.DataFrame(task_data)
        st.dataframe(df, use_container_width=True)

        # Task details section
        st.subheader("Task Details")
        selected_task_id = st.selectbox(
            "Select task to view details:",
            options=[task.get("id", "N/A") for task in tasks],
            index=0,
        )

        logger.debug(f"Выбрана задача: {selected_task_id}")

        if selected_task_id and selected_task_id != "N/A":
            # Find the selected task
            selected_task = next(
                (task for task in tasks if task.get("id") == selected_task_id), None
            )

            if selected_task:
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Basic Information:**")
                    st.write(f"Status: {selected_task.get('status', 'N/A')}")
                    st.write(f"Created: {selected_task.get('created_at', 'N/A')}")
                    st.write(f"Completed: {selected_task.get('completed_at', 'N/A')}")

                    if selected_task.get("status") in ["pending", "processing"]:
                        # Add auto-refresh for pending/processing tasks
                        auto_refresh = st.checkbox("Auto-refresh status", value=True)
                        if auto_refresh:
                            logger.info(
                                f"Автообновление статуса задачи {selected_task.get('id')}"
                            )
                            task_status = get_task_status(selected_task.get("id"))
                            st.write("**Current Status:**")
                            st.json(task_status)
                            logger.debug("Ожидание 5 секунд перед обновлением...")
                            time.sleep(5)
                            st.rerun()

                with col2:
                    if "output_data" in selected_task and selected_task["output_data"]:
                        st.write("**Results:**")
                        st.json(selected_task["output_data"])
                    elif (
                        "error_message" in selected_task
                        and selected_task["error_message"]
                    ):
                        error_message = selected_task["error_message"]
                        logger.error(
                            f"Ошибка задачи {selected_task_id}: {error_message}"
                        )
                        st.error(f"Error: {error_message}")
                    else:
                        if selected_task.get("status") in ["pending", "processing"]:
                            logger.info(
                                f"Задача {selected_task_id} все еще обрабатывается."
                            )
                            st.info(
                                "Task is still processing. Results will appear here when complete."
                            )
                        else:
                            logger.warning(
                                f"Результаты для задачи {selected_task_id} недоступны."
                            )
                            st.warning("No results available for this task.")
            else:
                logger.warning(f"Детали задачи {selected_task_id} не найдены.")
                st.warning("Task details not found.")
else:
    logger.error("Не удалось получить историю задач.")
    st.error("Failed to retrieve task history. Please try again later.")
