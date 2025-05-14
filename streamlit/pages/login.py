# ITMO-ML-Services/streamlit/pages/login.py
import streamlit as st
from utils.auth import login
from utils.api import register

st.set_page_config(
    page_title="Login - ML Classification", page_icon="🔑", layout="centered"
)

st.title("Login")

# Tabs for login and registration
tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log In")

    if submit:
        if email and password:
            with st.spinner("Logging in..."):
                if login(email, password):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
        else:
            st.warning("Please enter both email and password.")

with tab2:
    with st.form("register_form"):
        new_email = st.text_input("Email")
        new_full_name = st.text_input("Full Name")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        register_button = st.form_submit_button("Register")

    if register_button:
        if new_email and new_full_name and new_password:
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            else:
                with st.spinner("Registering..."):
                    result = register(new_email, new_password, new_full_name)
                    if result:
                        st.success("Registration successful! Please log in.")
                    else:
                        st.error(
                            "Registration failed. Please try a different email or check your connection."
                        )
        else:
            st.warning("Please fill out all fields.")
