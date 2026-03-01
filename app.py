import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Set page to wide mode
st.set_page_config(page_title="Karibu Task Manager", layout="wide")

# 1. Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Pull URL from Secrets
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet_url"]
except Exception:
    st.error("Missing 'spreadsheet_url' in Streamlit Secrets!")
    st.stop()

def load_wo_data():
    """Load WO data and clean WO Number column for better searching"""
    data = conn.read(spreadsheet=SHEET_URL, worksheet="WO_Log", ttl=0)
    data.columns = [str(c).strip() for c in data.columns]
    
    # Fix for search: remove .0 from numbers and convert to clean text
    if 'WO Number' in data.columns:
        data['WO Number'] = (
            data['WO Number']
            .astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.strip()
        )
    return data

def load_user_list():
    """Explicitly load names from 'users' tab"""
    try:
        # We read the 'users' worksheet
        user_data = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
        
        # Clean up column headers (lowercase and no spaces)
        user_data.columns = [str(c).strip().lower() for c in user_data.columns]
        
        # Look for a column named 'Name'
        if 'Name' in user_data.columns:
            # Get all non-empty names as a list
            name_list = user_data['name'].dropna().astype(str).str.strip().unique().tolist()
            # Filter out empty strings
            valid_names = [n for n in name_list if n != ""]
            return sorted(valid_names)
        else:
            return ["Admin", "Unassigned"]
    except:
        return ["Admin", "Unassigned"]

st.title("📋 Karibu Active Task Manager")

try:
    # Initial Data Load
    df = load_wo_data()
    # We load the names here to use in the dropdown below
    staff_names = load_user_list()

    # --- SEARCH & EDIT SECTION ---
    st.subheader("🔍 Search & Update Specific WO")
    
    col_search, col_clear = st.columns([4, 1])
    
    if 'search_val' not in st.session_state:
        st.session_state.search_val = ""

    search_query = col_search.text_input(
        "Enter WO Number", 
        value=st.session_state.search_val,
        placeholder="Search any WO number..."
    ).strip()

    if col_clear.button("Clear Search", use_container_width=True):
        st.session_state.search_val = ""
        st.rerun()

    if search_query:
        match = df[df['WO Number'] == str(search_query)]

        if not match.empty:
            row = match.iloc[0]
            idx = match.index[0]

            with st.container(border=True):
                st.write(f"### Editing Work Order #{search_query}")
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Client:** {row['Client_Name_Display']}")
                c2.write(f"**Category:** {row['Category']}")
                c3.write(f"**Current Status:** {row['Status']}")
                
                st.markdown("---")
                edit_col1, edit_col2 = st.columns(2)
                
                # 1. Status Dropdown
                status_list = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"]
                curr_s = str(row['Status']).strip()
                s_idx = status_list.index(curr_s) if curr_s in status_list else 0
                new_status = edit_col1.selectbox("Change Status", status_list, index=s_idx)

                # 2. Staff Dropdown (Reassign To)
                # Combine our sheet names with 'Admin' and 'Unassigned'
                dropdown_options = sorted(list(set(["Admin", "Unassigned"] + staff_names)))
                
                curr_a = str(row['Assigned To']).strip()
                # If current person isn't in our list (like an old email), add it temporarily
                if curr_a not in dropdown_options and curr_a != 'nan' and curr_a != "":
                    dropdown_options.append(curr_a)
                
                try:
                    a_idx = dropdown_options.index(curr_a)
                except:
                    a_idx = 0
                
                new_assignee = edit_col2.selectbox("Reassign To", dropdown_options, index=a_idx)

                if st.button("Save Changes ✅", use_container_width=True, type="primary"):
                    df.at[idx, 'Status'] = new_status
                    df.at[idx, 'Assigned To'] = new_assignee
                    conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df)
                    st.success(f"WO #{search_query} Updated!")
                    st.rerun()
        else:
            st.error(f"Work Order '{search_query}' not found.")

    # --- FILTERED ACTIVE TASKS TABLE ---
    st.divider()
    st.subheader("🚀 Active Tasks")

    # Filter strictly for Pending/In Progress or Unassigned
    # AND strictly exclude Completed/Cancelled
    active_df = df[
        (df['Status'].isin(['Pending', 'In Progress'])) | 
        (df['Assigned To'].isna()) | 
        (df['Assigned To'].str.lower() == 'unassigned') |
        (df['Assigned To'] == '')
    ]
    
    # Final exclusion to make sure no 'Completed' ones sneak in
    final_view = active_df[~active_df['Status'].isin(['Completed', 'Cancelled'])]

    if not final_view.empty:
        st.dataframe(
            final_view[['WO Number', 'Date', 'Client_Name_Display', 'Status', 'Assigned To']], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No active tasks found. Everything is completed!")

except Exception as e:
    st.error("Application Error")
    st.write(f"Details: {e}")
