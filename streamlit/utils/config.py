# ITMO-ML-Services/streamlit/utils/config.py
import os

# API URL for the ML service
API_URL = os.getenv("API_URL", "http://app:8000")

# Token session key for Streamlit
TOKEN_SESSION_KEY = "access_token"
USER_SESSION_KEY = "user_info"
