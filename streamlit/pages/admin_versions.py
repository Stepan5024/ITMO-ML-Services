# ITMO-ML-Services/streamlit/pages/admin_versions.py
import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from loguru import logger

from utils.auth import check_admin_access
from utils.api import (
    admin_list_models,
    admin_list_model_versions,
    admin_get_version,
    admin_upload_model_version,
    admin_delete_version,
    admin_set_default_version,
)

# Check if user has admin privileges
logger.debug("Проверка прав администратора...")
if not check_admin_access():
    st.stop()

st.set_page_config(page_title="Admin - Model Versions", page_icon="📁", layout="wide")

st.title("Model Versions Management")
st.write("Manage model versions, upload new ones, and set default versions.")

# Get all models to select from
models_response = admin_list_models()

if not models_response or "items" not in models_response:
    st.error("Failed to load models. Please check your connection or permissions.")
    st.stop()

models = models_response["items"]
if not models:
    st.warning("No models found. Please create a model first.")
    st.page_link("pages/admin_models.py", label="Create Models", icon="➕")
    st.stop()

# Model selection
selected_model_id = st.selectbox(
    "Select model:",
    options=[model["id"] for model in models],
    format_func=lambda x: next((m["name"] for m in models if m["id"] == x), x),
)

# Get selected model name
selected_model_name = next(
    (m["name"] for m in models if m["id"] == selected_model_id), "Unknown model"
)
st.subheader(f"Versions for: {selected_model_name}")

# Tabs for operations
tab1, tab2 = st.tabs(["View Versions", "Upload New Version"])

with tab1:
    # Get versions for selected model
    versions_response = admin_list_model_versions(selected_model_id)
    if versions_response and "items" in versions_response:
        versions = versions_response["items"]

        if versions:
            # Convert to DataFrame for better display
            versions_df = pd.DataFrame(
                [
                    {
                        "ID": version["id"],
                        "Version": version["version"],
                        "Default": "✓" if version["is_default"] else "",
                        "Status": version["status"],
                        "Size": f"{version['file_size']/1024:.2f} KB"
                        if version.get("file_size")
                        else "N/A",
                        "Created": datetime.fromisoformat(
                            version["created_at"]
                        ).strftime("%Y-%m-%d %H:%M"),
                    }
                    for version in versions
                ]
            )

            st.dataframe(
                versions_df,
                use_container_width=True,
                column_config={
                    "Default": st.column_config.TextColumn("Default", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                },
            )

            # Version details section
            st.subheader("Version Details")
            selected_version_id = st.selectbox(
                "Select version:",
                options=[version["id"] for version in versions],
                format_func=lambda x: next(
                    (v["version"] for v in versions if v["id"] == x), x
                ),
            )

            if selected_version_id:
                version_details = admin_get_version(selected_version_id)

                if version_details:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Version:** {version_details['version']}")
                        st.markdown(f"**Status:** {version_details['status']}")
                        st.markdown(f"**File Path:** {version_details['file_path']}")
                        st.markdown(
                            f"**File Size:** {version_details.get('file_size', 'N/A')} bytes"
                        )
                        st.markdown(
                            f"**Created By:** {version_details.get('created_by', 'N/A')}"
                        )
                        st.markdown(
                            f"**Created At:** {datetime.fromisoformat(version_details['created_at'])}"
                            f".strftime('%Y-%m-%d %H:%M:%S')"
                        )
                        st.markdown(
                            f"**Updated At:** {datetime.fromisoformat(version_details['updated_at'])}"
                            f".strftime('%Y-%m-%d %H:%M:%S')"
                        )

                        # Actions
                        st.subheader("Actions")
                        col1, col2 = st.columns(2)

                        with col1:
                            if not version_details["is_default"]:
                                if st.button(
                                    "Set as Default",
                                    key="set_default",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Setting as default..."):
                                        result = admin_set_default_version(
                                            selected_version_id
                                        )
                                        if result:
                                            st.success(
                                                "Version set as default successfully!"
                                            )
                                            st.rerun()
                                        else:
                                            st.error("Failed to set version as default")
                            else:
                                st.info("This is already the default version")

                        with col2:
                            if not version_details["is_default"]:
                                if st.button(
                                    "Delete Version",
                                    key="delete_version",
                                    type="primary",
                                    use_container_width=True,
                                ):
                                    if st.checkbox("Confirm deletion"):
                                        with st.spinner("Deleting version..."):
                                            result = admin_delete_version(
                                                selected_version_id
                                            )
                                            if result:
                                                st.success(
                                                    "Version deleted successfully!"
                                                )
                                                st.rerun()
                                            else:
                                                st.error("Failed to delete version")
                            else:
                                st.warning("Cannot delete default version")

                    with col2:
                        # Display parameters and metrics
                        st.subheader("Parameters")
                        st.json(version_details.get("parameters", {}))

                        st.subheader("Metrics")
                        st.json(version_details.get("metrics", {}))

                else:
                    st.error("Failed to load version details")
        else:
            st.info("No versions found for this model")
            st.write("Use the 'Upload New Version' tab to upload your first version.")
    else:
        st.error(
            "Failed to load versions. Please check your connection or permissions."
        )

with tab2:
    st.header("Upload New Model Version")

    with st.form("upload_version_form"):
        version_number = st.text_input(
            "Version Number", placeholder="e.g., 1.0.0", help="Semantic version number"
        )

        # Model file upload
        st.subheader("Model File")
        model_file = st.file_uploader(
            "Upload model file (.joblib or .pkl)", type=["joblib", "pkl"]
        )

        # Optional vectorizer
        st.subheader("Vectorizer (Optional)")
        vectorizer_file = st.file_uploader(
            "Upload vectorizer file (.joblib or .pkl)", type=["joblib", "pkl"]
        )

        # Metrics and parameters
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Metrics (JSON)")
            default_metrics = {
                "accuracy": 0.85,
                "precision": 0.83,
                "recall": 0.82,
                "f1_score": 0.825,
            }
            metrics_json = st.text_area(
                "Metrics", value=json.dumps(default_metrics, indent=2), height=150
            )

        with col2:
            st.subheader("Parameters (JSON)")
            default_params = {"max_features": 5000, "min_df": 5, "ngram_range": [1, 2]}
            params_json = st.text_area(
                "Parameters", value=json.dumps(default_params, indent=2), height=150
            )

        # Status selection
        status = st.selectbox(
            "Version Status",
            options=["TRAINED", "VALIDATED", "DEPLOYED", "ARCHIVED"],
            index=0,
        )

        submit_upload = st.form_submit_button("Upload Version")

    if submit_upload:
        if not version_number:
            st.warning("Please enter a version number")
        elif not model_file:
            st.warning("Please upload a model file")
        else:
            try:
                # Validate JSON
                metrics_dict = json.loads(metrics_json)
                params_dict = json.loads(params_json)

                # Prepare files for upload
                model_file_bytes = io.BytesIO(model_file.getvalue())
                model_file_bytes.name = model_file.name

                vectorizer_file_bytes = None
                if vectorizer_file:
                    vectorizer_file_bytes = io.BytesIO(vectorizer_file.getvalue())
                    vectorizer_file_bytes.name = vectorizer_file.name

                with st.spinner("Uploading model version..."):
                    result = admin_upload_model_version(
                        model_id=selected_model_id,
                        version=version_number,
                        model_file=model_file_bytes,
                        vectorizer_file=vectorizer_file_bytes,
                        metrics=metrics_json,
                        parameters=params_json,
                        status=status,
                    )

                    if result:
                        st.success(f"Version {version_number} uploaded successfully!")
                        st.json(result)
                    else:
                        st.error("Failed to upload model version")

            except json.JSONDecodeError:
                st.error("Invalid JSON in metrics or parameters. Please check and fix.")
            except Exception as e:
                st.error(f"Error uploading version: {str(e)}")

st.divider()
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/admin.py", label="Back to Admin Dashboard", icon="🔙")
with col2:
    st.page_link("pages/admin_models.py", label="Manage Models", icon="🧮")

logger.info("Admin versions page loaded successfully")
