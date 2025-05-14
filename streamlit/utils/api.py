# ITMO-ML-Services/streamlit/utils/api.py
import requests
import streamlit as st
from .config import API_URL, TOKEN_SESSION_KEY


def get_headers():
    """Get headers with authorization token."""
    token = st.session_state.get(TOKEN_SESSION_KEY)
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def login(email, password):
    """Log in to the ML service."""
    response = requests.post(
        f"{API_URL}/api/v1/auth/login", data={"username": email, "password": password}
    )
    return response.json() if response.ok else None


def register(email, password, full_name):
    """Register a new user."""
    response = requests.post(
        f"{API_URL}/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    return response.json() if response.ok else None


def get_user_info():
    """Get current user information."""
    response = requests.get(f"{API_URL}/api/v1/auth/me", headers=get_headers())
    return response.json() if response.ok else None


def get_available_models():
    """Get list of available classification models."""
    response = requests.get(f"{API_URL}/api/v1/models", headers=get_headers())
    return response.json() if response.ok else None


def classify_text(text, model_id=None, async_execution=False):
    """Classify a single text."""
    payload = {"text": text, "model_id": model_id, "async_execution": async_execution}
    response = requests.post(
        f"{API_URL}/api/v1/classify", json=payload, headers=get_headers()
    )
    return response.json() if response.ok else None


def batch_classify(texts, model_id=None):
    """Classify a batch of texts."""
    payload = {"texts": texts, "model_id": model_id, "async_execution": True}
    response = requests.post(
        f"{API_URL}/api/v1/classify-batch", json=payload, headers=get_headers()
    )
    return response.json() if response.ok else None


def get_task_status(task_id):
    """Get the status of an async task."""
    response = requests.get(f"{API_URL}/api/v1/tasks/{task_id}", headers=get_headers())
    return response.json() if response.ok else None


def get_user_tasks(page=1, size=10):
    """Get list of user tasks."""
    response = requests.get(
        f"{API_URL}/api/v1/tasks/?page={page}&size={size}", headers=get_headers()
    )
    return response.json() if response.ok else None


def get_user_balance():
    """Get current user balance."""
    response = requests.get(f"{API_URL}/api/v1/billing/balance", headers=get_headers())
    return response.json() if response.ok else None


def add_funds(amount):
    """Add funds to user balance."""
    payload = {"amount": amount}
    response = requests.post(
        f"{API_URL}/api/v1/billing/deposit", json=payload, headers=get_headers()
    )
    return response.json() if response.ok else None
