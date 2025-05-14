# ITMO-ML-Services/streamlit/pages/admin_stats.py
import streamlit as st
import pandas as pd
import numpy as np

from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from loguru import logger

from utils.auth import check_admin_access
from utils.api import get_user_tasks

# Check if user has admin privileges
logger.debug("Проверка прав администратора...")
if not check_admin_access():
    st.stop()

st.set_page_config(page_title="Admin - System Statistics", page_icon="📊", layout="wide")

st.title("System Statistics and Analytics")
st.write("Monitor system performance, usage metrics, and model analytics.")

# Time range selector
st.sidebar.header("Time Range")
time_range = st.sidebar.selectbox(
    "Select time range:",
    options=["Last 24 hours", "Last 7 days", "Last 30 days", "All time"],
    index=1,
)

# Refresh button
refresh = st.sidebar.button("Refresh Data", use_container_width=True)


# Mock data generation for demo
@st.cache_data(ttl=300)
def generate_mock_stats(time_range):
    # This would be replaced with actual API calls in production

    # Date range
    end_date = datetime.now()
    if time_range == "Last 24 hours":
        start_date = end_date - timedelta(days=1)
        periods = 24
        freq = "H"
    elif time_range == "Last 7 days":
        start_date = end_date - timedelta(days=7)
        periods = 7
        freq = "D"
    elif time_range == "Last 30 days":
        start_date = end_date - timedelta(days=30)
        periods = 30
        freq = "D"
    else:  # All time
        start_date = end_date - timedelta(days=90)
        periods = 90
        freq = "D"

    print(freq)
    # Generate timestamp series
    date_range = pd.date_range(start=start_date, end=end_date, periods=periods)

    # API calls data
    api_calls = pd.DataFrame(
        {
            "timestamp": date_range,
            "total_calls": np.random.randint(100, 1000, size=len(date_range)),
            "success_rate": np.random.uniform(0.95, 1.0, size=len(date_range)),
            "avg_response_time": np.random.uniform(50, 200, size=len(date_range)),
        }
    )

    # Model usage data
    models = ["Sentiment Analysis", "Text Classification", "Topic Modeling"]
    model_usage = pd.DataFrame(
        {
            "model": np.random.choice(models, size=len(date_range) * len(models)),
            "timestamp": np.repeat(date_range, len(models)),
            "calls": np.random.randint(10, 300, size=len(date_range) * len(models)),
            "avg_confidence": np.random.uniform(
                0.7, 0.95, size=len(date_range) * len(models)
            ),
        }
    )

    # System metrics
    system_metrics = pd.DataFrame(
        {
            "timestamp": date_range,
            "cpu_usage": np.random.uniform(10, 80, size=len(date_range)),
            "memory_usage": np.random.uniform(20, 75, size=len(date_range)),
            "disk_usage": np.random.uniform(30, 60, size=len(date_range)),
        }
    )

    # User stats
    user_stats = {
        "total_users": np.random.randint(100, 500),
        "active_today": np.random.randint(20, 100),
        "new_this_week": np.random.randint(5, 30),
        "admin_users": np.random.randint(3, 10),
    }

    # Model performance metrics
    model_metrics = pd.DataFrame(
        {
            "model": models,
            "accuracy": np.random.uniform(0.8, 0.95, size=len(models)),
            "precision": np.random.uniform(0.75, 0.9, size=len(models)),
            "recall": np.random.uniform(0.7, 0.9, size=len(models)),
            "f1_score": np.random.uniform(0.75, 0.92, size=len(models)),
        }
    )

    return {
        "api_calls": api_calls,
        "model_usage": model_usage,
        "system_metrics": system_metrics,
        "user_stats": user_stats,
        "model_metrics": model_metrics,
    }


# Get stats data
with st.spinner("Loading statistics..."):
    # This would be actual API calls in production
    data = generate_mock_stats(time_range)

# Dashboard layout
# Row 1: Key metrics
st.subheader("Key Performance Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_api_calls = int(data["api_calls"]["total_calls"].mean())
    st.metric(
        "Avg API Calls",
        f"{avg_api_calls}/day",
        f"{int(avg_api_calls * 0.05)}",
        help="Average number of API calls per day",
    )

with col2:
    avg_success = data["api_calls"]["success_rate"].mean() * 100
    st.metric(
        "API Success Rate",
        f"{avg_success:.2f}%",
        f"{(avg_success - 97):.2f}%",
        help="Percentage of successful API responses",
    )

with col3:
    avg_response = data["api_calls"]["avg_response_time"].mean()
    st.metric(
        "Avg Response Time",
        f"{avg_response:.0f} ms",
        f"{-5 if avg_response < 150 else 10}",
        help="Average API response time in milliseconds",
        delta_color="inverse",
    )

with col4:
    active_users = data["user_stats"]["active_today"]
    st.metric(
        "Active Users Today",
        active_users,
        f"{np.random.randint(-5, 15)}",
        help="Number of users active in the last 24 hours",
    )

# Row 2: Charts
st.subheader("Usage Analytics")
tab1, tab2, tab3 = st.tabs(["API Calls", "Model Usage", "System Performance"])

with tab1:
    # API calls over time
    fig = px.line(
        data["api_calls"],
        x="timestamp",
        y="total_calls",
        title="API Calls Over Time",
        labels={"timestamp": "Date", "total_calls": "Number of Calls"},
    )
    st.plotly_chart(fig, use_container_width=True)

    # Success rate over time
    fig = px.line(
        data["api_calls"],
        x="timestamp",
        y="success_rate",
        title="API Success Rate Over Time",
        labels={"timestamp": "Date", "success_rate": "Success Rate"},
        range_y=[0.9, 1.0],
    )
    fig.update_layout(yaxis_tickformat=".2%")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    # Model usage comparison
    fig = px.bar(
        data["model_usage"].groupby("model").sum().reset_index(),
        x="model",
        y="calls",
        title="Total Calls by Model",
        labels={"model": "Model", "calls": "Number of Calls"},
        color="model",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Model usage over time
    fig = px.line(
        data["model_usage"].groupby(["timestamp", "model"]).sum().reset_index(),
        x="timestamp",
        y="calls",
        color="model",
        title="Model Usage Over Time",
        labels={"timestamp": "Date", "calls": "Number of Calls", "model": "Model"},
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    # System metrics over time
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["system_metrics"]["timestamp"],
            y=data["system_metrics"]["cpu_usage"],
            mode="lines",
            name="CPU Usage %",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["system_metrics"]["timestamp"],
            y=data["system_metrics"]["memory_usage"],
            mode="lines",
            name="Memory Usage %",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["system_metrics"]["timestamp"],
            y=data["system_metrics"]["disk_usage"],
            mode="lines",
            name="Disk Usage %",
        )
    )
    fig.update_layout(
        title="System Resource Usage Over Time",
        xaxis_title="Date",
        yaxis_title="Usage Percentage",
        yaxis=dict(range=[0, 100]),
    )
    st.plotly_chart(fig, use_container_width=True)

# Row 3: Model Performance and User Statistics
st.subheader("Model Performance")

# Model metrics comparison
fig = px.bar(
    data["model_metrics"],
    x="model",
    y=["accuracy", "precision", "recall", "f1_score"],
    title="Model Performance Metrics",
    barmode="group",
    labels={"model": "Model", "value": "Score", "variable": "Metric"},
)
fig.update_layout(yaxis_range=[0, 1])
st.plotly_chart(fig, use_container_width=True)

# User statistics
st.subheader("User Statistics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Users", data["user_stats"]["total_users"])
with col2:
    st.metric("Active Users", data["user_stats"]["active_today"])
with col3:
    st.metric("New This Week", data["user_stats"]["new_this_week"])
with col4:
    st.metric("Admin Users", data["user_stats"]["admin_users"])

# Recent Activity
st.subheader("Recent Activity")

# This would be replaced with actual data from the backend
recent_tasks = get_user_tasks(page=1, size=5)
if recent_tasks and "items" in recent_tasks:
    tasks = recent_tasks["items"]
    if tasks:
        # Format and display tasks
        tasks_df = pd.DataFrame(
            [
                {
                    "Task ID": task.get("id", "N/A")[:8],
                    "Model": task.get("model_id", "N/A")[:8],
                    "Status": task.get("status", "N/A"),
                    "Created": task.get("created_at", "N/A"),
                    "Duration": f"{task.get('duration', 0):.2f}s"
                    if task.get("duration")
                    else "N/A",
                }
                for task in tasks
            ]
        )
        st.dataframe(tasks_df, use_container_width=True)
    else:
        st.info("No recent tasks found.")
else:
    # If API call fails, show sample data
    st.info("Recent activity data could not be loaded. Showing sample data.")
    sample_df = pd.DataFrame(
        [
            {
                "Task ID": f"task{i}",
                "Model": f"model{i}",
                "Status": "completed",
                "Created": datetime.now() - timedelta(minutes=i * 10),
                "Duration": f"{np.random.random()*5:.2f}s",
            }
            for i in range(1, 6)
        ]
    )
    st.dataframe(sample_df, use_container_width=True)

# Navigation
st.divider()
st.page_link("pages/admin.py", label="Back to Admin Dashboard", icon="🔙")

logger.info("Admin stats page loaded successfully")
