import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Set page to wide mode for better visibility of the log
st.set_page_config(page_title="Work Order Manager", layout="wide")

# 1. Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Configuration - Replace with your actual full Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit#gid=0"

def load_wo_data():
    """Load Work Order data from the WO_Log tab"""
    data = conn.read(spreadsheet=https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?gid=0#gid=0, worksheet="WO_Log", ttl=0)
    # Clean column names of hidden spaces
    data.columns = [str(c).strip() for c in data.columns]
    return data

def load_user_list():
    """Load staff names from the 'users' tab"""
    try:
        user_data = conn.read(spreadsheet=https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?gid=1731766061#gid=1731766061, worksheet="users", ttl=0)
        user_data.columns = [str(c).strip() for c in user_data.columns]
        # Return unique names as a list
        return sorted(user_data['name'].dropna().unique().tolist())
    except Exception:
        # Fallback list if 'users' tab isn't ready yet
        return ["Admin", "Unassigned"]

st.title("📋 Work Order Management System")

try:
    # Load all necessary data
    df = load_wo_data()
    staff_options = load_user_list()

    # --- SEARCH SECTION ---
    st.subheader("🔍 Search Work Order")
    search_query = st.text_input("Enter WO Number to Search", placeholder="e.g. 867")

    if search_query:
        # Filter data by WO Number
        match = df[df['WO Number'].astype(str) == str(search_query)]

        if not match.empty:
            row = match.iloc[0]
            idx = match.index[0]

            # --- DISPLAY ORDER DETAILS ---
            st.success(f"Work Order #{search_query} Found!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Date:** {row['Date']}")
                st.write(f"**Client:** {row['Client_Name_Display']}")
                st.write(f"**Phone:** {row['Client Phone']}")
            with col2:
                st.write(f"**Category:** {row['Category']}")
                st.write(f"**Subcategory:** {row['Subcategory']}")
                st.write(f"**Description:** {row['Description']}")
            with col3:
                st.write(f"**Current Status:** {row['Status']}")
                st.write(f"**Current Assignee:** {row['Assigned To']}")

            st.divider()

            # --- EDIT SECTION ---
            st.subheader("✏️ Update Order")
            
            edit_col1, edit_col2 = st.columns(2)
            
            status_options = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"]

            # Logic for Status Dropdown
            current_status = row['Status'] if row['Status'] in status_options else status_options[0]
            new_status = edit_col1.selectbox(
                "Update Status", 
                status_options, 
                index=status_options.index(current_status)
            )

            # Logic for Assigned To Dropdown (from 'users' tab)
            current_assignee = str(row['Assigned To']).strip()
            if current_assignee not in staff_options and current_assignee != 'nan':
                staff_options.append(current_assignee)
            
            # Find the correct index for the current person
            try:
                staff_idx = staff_options.index(current_assignee)
            except ValueError:
                staff_idx = 0

            new_assignee = edit_col2.selectbox(
                "Reassign To", 
                staff_options, 
                index=staff_idx
            )

            if st.button("Save Changes", use_container_width=True):
                # Update the row in the local dataframe
                df.at[idx, 'Status'] = new_status
                df.at[idx, 'Assigned To'] = new_assignee

                # Write back to Google Sheets
                conn.update(spreadsheet=https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?gid=0#gid=0, worksheet="WO_Log", data=df)
                
                st.balloons()
                st.success(f"WO #{search_query} updated successfully!")
                st.rerun()
        else:
            st.error(f"Work Order #{search_query} not found in the log.")

    # --- FULL LOG PREVIEW ---
    st.divider()
    st.subheader("All Active Work Orders")
    # Show summary table
    st.dataframe(df[['WO Number', 'Date', 'Client_Name_Display', 'Category', 'Status', 'Assigned To']], use_container_width=True)

    # --- ADD STAFF MEMBER SECTION ---
    with st.expander("👤 Admin: Add New Staff Member"):
        with st.form("new_user_form", clear_on_submit=True):
            new_name = st.text_input("Staff Name")
            new_email = st.text_input("Staff Email")
            new_role = st.selectbox("Role", ["Technician", "Admin", "Sales", "Designer"])
            
            if st.form_submit_button("Add User to Database"):
                if new_name:
                    # Load current users tab
                    users_df = conn.read(spreadsheet=https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?gid=1731766061#gid=1731766061, worksheet="users", ttl=0)
                    new_row = pd.DataFrame([{"email": new_email, "name": new_name, "role": new_role}])
                    updated_users = pd.concat([users_df, new_row], ignore_index=True)
                    # Update users tab
                    conn.update(spreadsheet=https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?gid=1731766061#gid=1731766061, worksheet="users", data=updated_users)
                    st.success(f"{new_name} added! Refresh to see in dropdown.")
                    st.rerun()

except Exception as e:
    st.error("Could not load Work Order Log.")
    st.write("Error Detail:", e)
