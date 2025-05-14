# ITMO-ML-Services/streamlit/pages/balance.py
import streamlit as st
from utils.auth import check_login
from utils.api import get_user_balance, add_funds

# Check login status
check_login()

st.set_page_config(page_title="Account Balance", page_icon="💰", layout="wide")

st.title("Account Balance")

# Get current balance
balance_info = get_user_balance()

if balance_info:
    # Display current balance
    balance = balance_info.get("balance", 0)
    currency = balance_info.get("currency", "USD")
    last_updated = balance_info.get("last_updated", "N/A")

    st.metric("Current Balance", f"{balance} {currency}")
    st.write(f"Last updated: {last_updated}")

    # Add funds section
    st.subheader("Add Funds")
    st.write("Use this form to add funds to your account.")

    with st.form("add_funds_form"):
        amount = st.number_input(
            "Amount to add", min_value=5.0, max_value=1000.0, value=10.0, step=5.0
        )
        payment_method = st.selectbox("Payment Method", ["Credit Card", "Demo"])
        submit = st.form_submit_button("Add Funds")

    if submit:
        # In a real app, this would redirect to a payment gateway
        # For this demo, we'll just call the API directly
        with st.spinner("Processing payment..."):
            result = add_funds(amount)

            if result:
                st.success(f"Successfully added {amount} {currency} to your account!")
                st.info("Please refresh to see your updated balance.")
                if st.button("Refresh Balance"):
                    st.rerun()
            else:
                st.error("Failed to add funds. Please try again later.")

    # Transaction history would go here in a real application
    st.subheader("Transaction History")
    st.info("Transaction history feature is coming soon.")

else:
    st.error("Failed to retrieve balance information. Please try again later.")
