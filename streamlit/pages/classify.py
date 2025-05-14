# ITMO-ML-Services/streamlit/pages/classify.py
import streamlit as st
from utils.auth import check_login
from utils.api import classify_text, get_available_models

# Check login status
check_login()

st.set_page_config(page_title="Text Classification", page_icon="📝", layout="wide")

st.title("Text Classification")
st.write("Submit text to classify using our machine learning models.")

# Get available models
models = get_available_models()
model_options = {}

if models and "items" in models:
    model_options = {
        f"{model['name']} - {model['model_type']}": model["id"]
        for model in models["items"]
    }
    model_options["Default Model"] = None
else:
    model_options["Default Model"] = None

# Classification form
with st.form("classification_form"):
    text = st.text_area("Enter text to classify:", height=200)

    col1, col2 = st.columns(2)
    with col1:
        model_name = st.selectbox("Select model:", list(model_options.keys()))
    with col2:
        async_execution = st.checkbox(
            "Asynchronous execution", help="Process in the background for longer texts"
        )

    submit = st.form_submit_button("Submit for Classification")

if submit and text:
    model_id = model_options[model_name]

    with st.spinner("Processing..."):
        result = classify_text(text, model_id, async_execution)

        if result:
            st.success("Classification complete!")

            if async_execution and "task_id" in result:
                st.info(f"Task submitted successfully! Task ID: {result['task_id']}")
                st.info("You can check the result in the History tab.")
            else:
                # Display result in a nice format
                st.subheader("Results:")

                col1, col2 = st.columns(2)

                with col1:
                    if "prediction" in result:
                        st.metric("Sentiment", result["prediction"])

                    if "confidence" in result:
                        st.metric("Confidence", f"{result['confidence']:.2%}")

                with col2:
                    if "execution_time_ms" in result:
                        st.metric(
                            "Processing Time", f"{result['execution_time_ms']} ms"
                        )

                    if "categories" in result and result["categories"]:
                        st.write("**Categories:**")
                        for category in result["categories"]:
                            st.write(f"- {category.capitalize()}")

                # Show raw JSON for advanced users
                with st.expander("View raw JSON result"):
                    st.json(result)
        else:
            st.error("Classification failed. Please try again or check your balance.")
