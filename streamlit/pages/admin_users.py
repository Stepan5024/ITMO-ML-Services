# ITMO-ML-Services/streamlit/pages/admin_users.py
import streamlit as st
import pandas as pd
from datetime import datetime
from loguru import logger

from utils.auth import check_admin_access
from utils.api import (
    admin_list_users,
    admin_get_user,
    admin_activate_user,
    admin_deactivate_user,
    admin_set_admin_status,
)

# Check if user has admin privileges
logger.debug("Проверка прав администратора...")
if not check_admin_access():
    st.stop()

st.set_page_config(page_title="Admin - User Management", page_icon="👥", layout="wide")

st.title("User Management")
st.write("View and manage user accounts in the ML service.")

# Filters for user list
col1, col2, col3 = st.columns(3)
with col1:
    search_term = st.text_input("Search by email or name")
with col2:
    status_filter = st.selectbox(
        "Filter by status",
        options=[None, True, False],
        format_func=lambda x: "All users"
        if x is None
        else ("Active" if x else "Inactive"),
    )
with col3:
    admin_filter = st.selectbox(
        "Filter by admin status",
        options=[None, True, False],
        format_func=lambda x: "All users"
        if x is None
        else ("Admins" if x else "Regular users"),
    )

# Pagination controls
col1, col2 = st.columns([3, 1])
with col1:
    st.write("Page and size:")
with col2:
    refresh = st.button("Refresh", use_container_width=True)

col1, col2 = st.columns([1, 3])
with col1:
    page = st.number_input("Page", min_value=1, value=1)
with col2:
    size = st.select_slider("Users per page", options=[10, 20, 50, 100], value=20)

# Get users list
with st.spinner("Loading users..."):
    users_response = admin_list_users(
        search=search_term,
        is_active=status_filter,
        is_admin=admin_filter,
        page=page,
        size=size,
    )

if users_response and "items" in users_response:
    users = users_response["items"]
    total = users_response.get("total", 0)
    pages = users_response.get("pages", 1)

    st.write(f"Showing {len(users)} of {total} users (Page {page} of {pages})")

    if users:
        # Convert to DataFrame for better display
        users_df = pd.DataFrame(
            [
                {
                    "ID": user["id"],
                    "Email": user["email"],
                    "Name": user["full_name"],
                    "Balance": f"${user['balance']:.2f}",
                    "Status": "Active" if user["is_active"] else "Inactive",
                    "Admin": "Yes" if user["is_admin"] else "No",
                }
                for user in users
            ]
        )

        st.dataframe(
            users_df,
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Admin": st.column_config.TextColumn("Admin", width="small"),
            },
        )

        # User details section
        st.subheader("User Details")
        selected_user_id = st.selectbox(
            "Select user:",
            options=[user["id"] for user in users],
            format_func=lambda x: next(
                (f"{u['email']} ({u['full_name']})" for u in users if u["id"] == x), x
            ),
        )

        if selected_user_id:
            user_details = admin_get_user(selected_user_id)

            if user_details:
                # Check if current user is viewing their own account
                current_user_id = st.session_state.get("user_info", {}).get("id")
                is_self = str(current_user_id) == str(selected_user_id)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Email:** {user_details['email']}")
                    st.markdown(f"**Full Name:** {user_details['full_name']}")
                    st.markdown(
                        f"**Account Status:** {'Active' if user_details['is_active'] else 'Inactive'}"
                    )
                    st.markdown(
                        f"**Admin Status:** {'Admin' if user_details['is_admin'] else 'Regular User'}"
                    )
                    st.markdown(f"**Balance:** ${float(user_details['balance']):.2f}")

                    # Show created/updated timestamps
                    if "created_at" in user_details:
                        created_at = datetime.fromisoformat(
                            user_details["created_at"].replace("Z", "+00:00")
                        )
                        st.markdown(
                            f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                        )

                    if "updated_at" in user_details:
                        updated_at = datetime.fromisoformat(
                            user_details["updated_at"].replace("Z", "+00:00")
                        )
                        st.markdown(
                            f"**Last Updated:** {updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
                        )

                with col2:
                    st.subheader("Actions")

                    # Don't allow changing own status
                    if is_self:
                        st.warning("You cannot modify your own account status")
                    else:
                        col1, col2 = st.columns(2)

                        # Activate/Deactivate
                        with col1:
                            if user_details["is_active"]:
                                if st.button(
                                    "Deactivate User",
                                    key="deactivate_user",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Deactivating user..."):
                                        result = admin_deactivate_user(selected_user_id)
                                        if result:
                                            st.success("User deactivated successfully!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to deactivate user")
                            else:
                                if st.button(
                                    "Activate User",
                                    key="activate_user",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Activating user..."):
                                        result = admin_activate_user(selected_user_id)
                                        if result:
                                            st.success("User activated successfully!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to activate user")

                        # Toggle admin status
                        with col2:
                            if user_details["is_admin"]:
                                if st.button(
                                    "Remove Admin",
                                    key="remove_admin",
                                    use_container_width=True,
                                ):
                                    with st.spinner("Removing admin status..."):
                                        result = admin_set_admin_status(
                                            selected_user_id, False
                                        )
                                        if result:
                                            st.success(
                                                "Admin status removed successfully!"
                                            )
                                            st.rerun()
                                        else:
                                            st.error("Failed to remove admin status")
                            else:
                                if st.button(
                                    "Make Admin",
                                    key="make_admin",
                                    use_container_width=True,
                                ):
                                    if st.checkbox("Confirm granting admin privileges"):
                                        with st.spinner("Setting admin status..."):
                                            result = admin_set_admin_status(
                                                selected_user_id, True
                                            )
                                            if result:
                                                st.success(
                                                    "User granted admin privileges!"
                                                )
                                                st.rerun()
                                            else:
                                                st.error(
                                                    "Failed to grant admin privileges"
                                                )

                    # Transaction history would be implemented here in a real app
                    st.subheader("Account History")
                    st.info("Transaction history view is not implemented in this demo")

            else:
                st.error("Failed to load user details")
    else:
        st.info("No users found with the current filters")
else:
    st.error("Failed to load users list. Please check your connection or permissions.")

# Navigation
st.divider()
st.page_link("pages/admin.py", label="Back to Admin Dashboard", icon="🔙")

logger.info("Admin users page loaded successfully")
