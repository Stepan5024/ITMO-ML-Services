# ITMO-ML-Services/streamlit/pages/admin.py
import streamlit as st
from loguru import logger
from utils.auth import check_admin_access

# Check if user has admin privileges
logger.debug("Проверка прав администратора...")
if not check_admin_access():
    st.stop()

st.set_page_config(page_title="Admin Dashboard", page_icon="🔧", layout="wide")

st.title("Administration Dashboard")
st.write("Welcome to the ML Classification Service administration panel.")

# Display admin user info
user_info = st.session_state.get("user_info", {})
st.sidebar.write(
    f"Admin: {user_info.get('full_name', user_info.get('email', 'Admin'))}"
)

# Admin navigation
admin_pages = {
    "Models Management": "pages/admin_models.py",
    "Model Versions": "pages/admin_versions.py",
    "User Management": "pages/admin_users.py",
    "System Stats": "pages/admin_stats.py",
}

st.sidebar.header("Admin Navigation")
for page_name, page_path in admin_pages.items():
    st.sidebar.page_link(page_path, label=page_name)

# Return to main app
st.sidebar.divider()
st.sidebar.page_link("app.py", label="Back to Main App")

# Main content - quick stats and overview
col1, col2 = st.columns(2)

with col1:
    st.subheader("Quick Actions")

    st.button(
        "Refresh Service Cache",
        use_container_width=True,
        help="Clear and refresh the service cache",
    )

    st.button(
        "Check Service Health",
        use_container_width=True,
        help="Run diagnostics on service components",
    )

with col2:
    st.subheader("System Status")
    st.metric("API Status", "Online", "Good")
    st.metric("Database Status", "Connected", "Good")
    st.metric("ML Service", "Running", "Good")

# Overview cards
st.subheader("Overview")
col1, col2, col3 = st.columns(3)

with col1:
    with st.container():
        st.subheader("ML Models")
        st.write("Manage classification models")
        st.page_link("pages/admin_models.py", label="Open ML Models", icon="🧮")

with col2:
    with st.container():
        st.subheader("Users")
        st.write("Manage user accounts")
        st.page_link("pages/admin_users.py", label="Open Users", icon="👥")

with col3:
    with st.container():
        st.subheader("System Stats")
        st.write("View system statistics")
        st.page_link("pages/admin_stats.py", label="Open Stats", icon="📊")

# Add some detailed information
st.subheader("Administrative Functions")
st.markdown(
    """
This administration panel provides the following capabilities:

- **Models Management**: Create, edit, and delete ML models
- **Model Versions**: Upload new model versions and manage existing ones
- **User Management**: Manage user accounts, permissions, and balances
- **System Statistics**: View system usage statistics and service health
"""
)

logger.info("Admin dashboard loaded successfully")
