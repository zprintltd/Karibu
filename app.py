import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Set page configuration
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
    """Load WO data and clean columns/numbers"""
    data = conn.read(spreadsheet=SHEET_URL, worksheet="WO_Log", ttl=0)
    data.columns = [str(c).strip() for c in data.columns]
    
    if 'WO Number' in data.columns:
        # Convert to string, remove .0, and make uppercase for easier matching
        data['WO Number'] = (
            data['WO Number']
            .astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.strip()
            .str.upper()
        )
    return data

def load_user_list():
    """Load names from 'users' tab, Column B ('Name')"""
    try:
        user_data = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
        # Standardize headers to lowercase to find 'name' column
        user_data.columns = [str(c).strip().lower() for c in user_data.columns]
        
        if 'name' in user_data.columns:
            name_list = user_data['name'].dropna().astype(str).str.strip().unique().tolist()
            return [n for n in name_list if n != ""]
        return []
    except Exception as e:
        return []

st.title("📋 Karibu Active Task Manager")

try:
    # Initial Data Load
    df = load_wo_data()
    staff_names = load_user_list()

    # --- SEARCH & EDIT SECTION ---
    st.subheader("🔍 Search & Update Specific WO")
    col_search, col_clear = st.columns([4, 1])
    
    if 'search_val' not in st.session_state:
        st.session_state.search_val = ""

    # Search input is converted to uppercase to match the cleaned df
    search_query = col_search.text_input(
        "Enter WO Number", 
        value=st.session_state.search_val,
        placeholder="Search (e.g., 1200 or WO-867)..."
    ).strip().upper()

    if col_clear.button("Clear Search", use_container_width=True):
        st.session_state.search_val = ""
        st.rerun()

    if search_query:
        match = df[df['WO Number'] == search_query]

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
                
                # 1. Status Dropdown (Standardized list)
                status_list = ["Pending", "In progress", "Completed", "On Hold", "Cancelled"]
                curr_s = str(row['Status']).strip()
                
                # Find index regardless of case (pending vs Pending)
                try:
                    s_idx = [s.lower() for s in status_list].index(curr_s.lower())
                except ValueError:
                    s_idx = 0
                
                new_status = edit_col1.selectbox("Change Status", status_list, index=s_idx)

                # 2. Staff Dropdown (Reassign To)
                dropdown_options = sorted(list(set(["Admin", "Unassigned"] + staff_names)))
                curr_a = str(row['Assigned To']).strip()
                
                if curr_a not in dropdown_options and curr_a.lower() != 'nan' and curr_a != "":
                    dropdown_options.append(curr_a)
                
                try:
                    a_idx = dropdown_options.index(curr_a)
                except ValueError:
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

    # Force Status and Assigned To to string to prevent errors
    df['Status'] = df['Status'].astype(str)
    df['Assigned To'] = df['Assigned To'].astype(str)

    # CASE-INSENSITIVE FILTERING
    is_pending = df['Status'].str.lower() == 'pending'
    is_in_progress = df['Status'].str.lower() == 'in progress'
    is_unassigned = (
        (df['Assigned To'].str.lower() == 'nan') | 
        (df['Assigned To'].str.lower() == 'unassigned') | 
        (df['Assigned To'].str.strip() == '')
    )
    
    active_mask = (is_pending | is_in_progress | is_unassigned)
    
    # Exclude Completed and Cancelled regardless of case
    final_view = df[active_mask]
    final_view = final_view[~final_view['Status'].str.lower().isin(['completed', 'cancelled'])]

    if not final_view.empty:
        st.dataframe(
            final_view[['WO Number', 'Date', 'Client_Name_Display', 'Status', 'Assigned To']], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No active tasks found (Pending, In progress, or Unassigned).")

except Exception as e:
    st.error("⚠️ Application Error")
    st.write(f"Details: {e}")
