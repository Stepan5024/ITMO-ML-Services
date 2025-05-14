# ITMO-ML-Services/streamlit/pages/admin_models.py
import streamlit as st
import json
import pandas as pd
from loguru import logger

from utils.auth import check_admin_access
from utils.api import (
    admin_list_models,
    admin_get_model,
    admin_create_model,
    admin_update_model,
    admin_delete_model,
    admin_activate_model,
    admin_deactivate_model,
)

logger.debug("Проверка прав администратора...")
if not check_admin_access():
    st.stop()

st.set_page_config(page_title="Admin - Models Management", page_icon="📊", layout="wide")

st.title("Models Management")
st.write("Create, view, and manage ML classification models.")


def format_schema_display(schema_str):
    try:
        # Parse the schema then format it
        schema = json.loads(schema_str)
        return json.dumps(schema, indent=2)
    except Exception:
        return schema_str


# Tabs for different model operations
tab1, tab2, tab3 = st.tabs(["View Models", "Create Model", "Edit Model"])

with tab1:
    st.header("Models List")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("Search by name or description")
    with col2:
        model_type_filter = st.selectbox(
            "Filter by model type",
            options=[
                None,
                "text_classification",
                "sentiment_analysis",
                "topic_modeling",
            ],
            format_func=lambda x: "All types" if x is None else x,
        )
    with col3:
        status_filter = st.selectbox(
            "Filter by status",
            options=[None, True, False],
            format_func=lambda x: "All statuses"
            if x is None
            else ("Active" if x else "Inactive"),
        )

    # Refresh button
    refresh = st.button("Refresh Models", use_container_width=True)

    # Get models list
    with st.spinner("Loading models..."):
        models_response = admin_list_models(
            search=search_term, model_type=model_type_filter, is_active=status_filter
        )

    if models_response and "items" in models_response:
        models = models_response["items"]
        if models:
            # Convert to DataFrame for better display
            models_df = pd.DataFrame(
                [
                    {
                        "ID": model["id"],
                        "Name": model["name"],
                        "Type": model["model_type"],
                        "Algorithm": model["algorithm"],
                        "Price": f"${float(model['price_per_call']):.4f}",
                        "Status": "Active" if model["is_active"] else "Inactive",
                    }
                    for model in models
                ]
            )

            st.dataframe(
                models_df,
                use_container_width=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                },
            )

            # Model details section
            st.subheader("Model Details")
            selected_model_id = st.selectbox(
                "Select model to view details:",
                options=[model["id"] for model in models],
                format_func=lambda x: next(
                    (m["name"] for m in models if m["id"] == x), x
                ),
            )

            if selected_model_id:
                model_details = admin_get_model(selected_model_id)

                if model_details:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Name:** {model_details['name']}")
                        st.markdown(f"**Description:** {model_details['description']}")
                        st.markdown(f"**Type:** {model_details['model_type']}")
                        st.markdown(f"**Algorithm:** {model_details['algorithm']}")
                        st.markdown(
                            f"**Price per call:** ${float(model_details['price_per_call']):.4f}"
                        )
                        st.markdown(
                            f"**Status:** {'Active' if model_details['is_active'] else 'Inactive'}"
                        )

                        # Actions for this model
                        st.subheader("Actions")
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            if model_details["is_active"]:
                                if st.button(
                                    "Deactivate Model",
                                    key="deactivate",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Deactivating model..."):
                                        result = admin_deactivate_model(
                                            selected_model_id
                                        )
                                        if result:
                                            st.success(
                                                "Model deactivated successfully!"
                                            )
                                            st.rerun()
                                        else:
                                            st.error("Failed to deactivate model")
                            else:
                                if st.button(
                                    "Activate Model",
                                    key="activate",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Activating model..."):
                                        result = admin_activate_model(selected_model_id)
                                        if result:
                                            st.success("Model activated successfully!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to activate model")

                        with col2:
                            st.page_link(
                                "pages/admin_versions.py",
                                label="Manage Versions",
                                icon="📁",
                                use_container_width=True,
                            )

                        with col3:
                            if st.button(
                                "Delete Model",
                                key="delete",
                                use_container_width=True,
                                type="primary",
                            ):
                                if st.checkbox("Confirm deletion"):
                                    with st.spinner("Deleting model..."):
                                        result = admin_delete_model(selected_model_id)
                                        if result:
                                            st.success("Model deleted successfully!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to delete model")

                    with col2:
                        st.subheader("Input Schema")
                        st.code(
                            format_schema_display(model_details["input_schema"]),
                            language="json",
                        )

                        st.subheader("Output Schema")
                        st.code(
                            format_schema_display(model_details["output_schema"]),
                            language="json",
                        )

                else:
                    st.error("Failed to load model details")
        else:
            st.info("No models found with the current filters")
    else:
        st.error(
            "Failed to load models list. Please check your connection or permissions."
        )

with tab2:
    st.header("Create New Model")

    with st.form("create_model_form"):
        name = st.text_input("Model Name", max_chars=100)
        description = st.text_area("Description", max_chars=500)

        col1, col2 = st.columns(2)

        with col1:
            model_type = st.selectbox(
                "Model Type",
                options=["classification", "sentiment_analysis", "topic_modeling"],
            )
            algorithm = st.text_input(
                "Algorithm",
                placeholder="e.g., RandomForest, BERT, logistic_regression.",
            )

        with col2:
            price_per_call = st.number_input(
                "Price Per Call",
                min_value=0.0001,
                max_value=10.0,
                value=0.01,
                step=0.001,
                format="%.4f",
            )
            is_active = st.checkbox("Active", value=True)

        st.subheader("Input Schema (JSON)")
        default_input = {"text": {"type": "string", "required": True}}
        input_schema = st.text_area(
            "Input Schema", value=json.dumps(default_input, indent=2), height=150
        )

        st.subheader("Output Schema (JSON)")
        default_output = {
            "sentiment": {"type": "string"},
            "confidence": {"type": "number"},
        }

        output_schema = st.text_area(
            "Output Schema", value=json.dumps(default_output, indent=2), height=150
        )

        submit = st.form_submit_button("Create Model")

    if submit:
        if name and description and model_type and algorithm:
            try:
                json.loads(input_schema)
                json.loads(output_schema)

                model_data = {
                    "name": name,
                    "description": description,
                    "model_type": model_type,
                    "algorithm": algorithm,
                    "price_per_call": price_per_call,
                    "is_active": is_active,
                    "input_schema": json.loads(input_schema),
                    "output_schema": json.loads(output_schema),
                }

                with st.spinner("Creating model..."):
                    result = admin_create_model(model_data)

                    if result:
                        st.success(f"Model '{name}' created successfully!")
                        st.json(result)
                        st.info("You can now upload model versions for this model.")
                    else:
                        st.error(
                            "Failed to create model. Please check your input and try again."
                        )

            except json.JSONDecodeError:
                st.error("Invalid JSON in schema fields. Please check and fix.")
        else:
            st.warning("Please fill in all required fields.")

with tab3:
    st.header("Edit Existing Model")

    # Get models list for selection
    models_response = admin_list_models()

    if models_response and "items" in models_response:
        models = models_response["items"]

        if models:
            # Model selection
            selected_model_id = st.selectbox(
                "Select model to edit:",
                options=[model["id"] for model in models],
                format_func=lambda x: next(
                    (m["name"] for m in models if m["id"] == x), x
                ),
            )

            if selected_model_id:
                # Get current model data
                current_model = admin_get_model(selected_model_id)

                if current_model:
                    with st.form("edit_model_form"):
                        name = st.text_input(
                            "Model Name", value=current_model["name"], max_chars=100
                        )
                        description = st.text_area(
                            "Description",
                            value=current_model["description"],
                            max_chars=500,
                        )

                        col1, col2 = st.columns(2)

                        with col1:
                            model_type = st.selectbox(
                                "Model Type",
                                options=[
                                    "classification",
                                    "sentiment_analysis",
                                    "topic_modeling",
                                ],
                                index=[
                                    "classification",
                                    "sentiment_analysis",
                                    "topic_modeling",
                                ].index(current_model["model_type"])
                                if current_model["model_type"]
                                in [
                                    "classification",
                                    "sentiment_analysis",
                                    "topic_modeling",
                                ]
                                else 0,
                            )
                            algorithm = st.text_input(
                                "Algorithm", value=current_model["algorithm"]
                            )

                        with col2:
                            current_price = float(current_model["price_per_call"])
                            initial_price = max(current_price, 0.0001)
                            price_per_call = st.number_input(
                                "Price Per Call",
                                min_value=0.0001,
                                max_value=10.0,
                                value=initial_price,
                                step=0.001,
                                format="%.4f",
                            )
                            is_active = st.checkbox(
                                "Active", value=current_model["is_active"]
                            )

                        st.subheader("Input Schema (JSON)")
                        input_schema = st.text_area(
                            "Input Schema",
                            value=format_schema_display(current_model["input_schema"]),
                            height=150,
                        )

                        st.subheader("Output Schema (JSON)")
                        output_schema = st.text_area(
                            "Output Schema",
                            value=format_schema_display(current_model["output_schema"]),
                            height=150,
                        )

                        submit_edit = st.form_submit_button("Update Model")

                    if submit_edit:
                        if name and description and model_type and algorithm:
                            try:
                                # Validate JSON schemas
                                json.loads(input_schema)
                                json.loads(output_schema)

                                model_data = {
                                    "name": name,
                                    "description": description,
                                    "model_type": model_type,
                                    "algorithm": algorithm,
                                    "price_per_call": price_per_call,
                                    "is_active": is_active,
                                    "input_schema": json.loads(input_schema),
                                    "output_schema": json.loads(output_schema),
                                }

                                with st.spinner("Updating model..."):
                                    result = admin_update_model(
                                        selected_model_id, model_data
                                    )

                                    if result:
                                        st.success(
                                            f"Model '{name}' updated successfully!"
                                        )
                                    else:
                                        st.error(
                                            "Failed to update model. Please check your input and try again."
                                        )

                            except json.JSONDecodeError:
                                st.error(
                                    "Invalid JSON in schema fields. Please check and fix."
                                )
                        else:
                            st.warning("Please fill in all required fields.")
                else:
                    st.error("Failed to load model data")
        else:
            st.info("No models found. Please create a model first.")
    else:
        st.error(
            "Failed to load models list. Please check your connection or permissions."
        )

# Navigation back buttons
st.divider()
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/admin.py", label="Back to Admin Dashboard", icon="🔙")
with col2:
    st.page_link("pages/admin_versions.py", label="Manage Model Versions", icon="📁")

logger.info("Admin models page loaded successfully")
