# ITMO-ML-Services/streamlit/utils/auth.py
import streamlit as st
from .config import TOKEN_SESSION_KEY, USER_SESSION_KEY
from .api import login as api_login, get_user_info


def check_login():
    """Check if user is logged in and redirect if not."""
    if TOKEN_SESSION_KEY not in st.session_state:
        st.switch_page("pages/login.py")

    # Also verify user info is available
    if USER_SESSION_KEY not in st.session_state:
        user_info = get_user_info()
        if user_info:
            st.session_state[USER_SESSION_KEY] = user_info
        else:
            # Invalid or expired token
            st.session_state.pop(TOKEN_SESSION_KEY, None)
            st.switch_page("pages/login.py")


def login(email, password):
    """Log in user and store token in session."""
    response = api_login(email, password)
    if response and "access_token" in response:
        st.session_state[TOKEN_SESSION_KEY] = response["access_token"]
        user_info = get_user_info()
        if user_info:
            st.session_state[USER_SESSION_KEY] = user_info
            return True
    return False


def logout():
    """Log out user by clearing session state."""
    st.session_state.clear()
