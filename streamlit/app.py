# ITMO-ML-Services/streamlit/app.py
from loguru import logger

import streamlit as st
from utils.auth import check_login, logout

st.set_page_config(
    page_title="ML Classification Service",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    check_login()
except Exception as e:
    logger.warning(f"Login check failed: {e}")
    st.switch_page("pages/login.py")

# Display sidebar with navigation
st.sidebar.title("ML Classification")

# Get user info
user_info = st.session_state.get("user_info", {})
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
    logout()
    st.rerun()

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

if submit and text:
    with st.spinner("Classifying..."):
        from utils.api import classify_text

        result = classify_text(text)

        if result:
            st.success("Classification complete!")
            st.json(result)
        else:
            st.error("Classification failed. Please try again or check your balance.")
