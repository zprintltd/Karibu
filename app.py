import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Work Order Manager", layout="wide")

# 1. Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Configuration - Ensure this URL is your WO_Log Google Sheet link
SHEET_URL = "PASTE_YOUR_URL_HERE"

def load_wo_data():
    # Reading the WO_Log tab
    data = conn.read(spreadsheet=SHEET_URL, worksheet="WO_Log", ttl=0)
    data.columns = [str(c).strip() for c in data.columns]
    return data

st.title("📋 Work Order Management System")

try:
    df = load_wo_data()

    # --- SEARCH SECTION ---
    st.subheader("🔍 Search Work Order")
    search_query = st.text_input("Enter WO Number to Search", placeholder="e.g. 867")

    if search_query:
        # Filter data by WO Number (handling it as a string to be safe)
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
                st.write(f"**Assigned To:** {row['Assigned To']}")

            st.divider()

            # --- EDIT SECTION ---
            st.subheader("✏️ Update Order")
            
            edit_col1, edit_col2 = st.columns(2)
            
            # Options for Status and Staff (You can customize these lists)
            status_options = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"]
            staff_options = ["Large.zprint@...", "Small.zprint@...", "Admin", "Unassigned"]

            # Set current values as defaults
            new_status = edit_col1.selectbox("Update Status", status_options, index=status_options.index(row['Status']) if row['Status'] in status_options else 0)
            new_assignee = edit_col2.selectbox("Reassign To", staff_options, index=staff_options.index(row['Assigned To']) if row['Assigned To'] in staff_options else 0)

            if st.button("Save Changes to Google Sheet"):
                # Update the specific row in our local dataframe
                df.at[idx, 'Status'] = new_status
                df.at[idx, 'Assigned To'] = new_assignee

                # Push the entire updated dataframe back to Google Sheets
                conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df)
                
                st.balloons()
                st.success(f"WO #{search_query} updated successfully!")
                st.rerun()
        else:
            st.error(f"Work Order #{search_query} not found in the log.")

    # --- FULL LOG PREVIEW ---
    st.divider()
    st.subheader("All Active Work Orders")
    st.dataframe(df[['WO Number', 'Date', 'Client_Name_Display', 'Category', 'Status', 'Assigned To']], use_container_width=True)

except Exception as e:
    st.error("Could not load Work Order Log.")
    st.write("Error Detail:", e)
