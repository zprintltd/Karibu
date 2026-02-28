import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Set page to wide mode
st.set_page_config(page_title="Work Order Manager", layout="wide")

# 1. Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Pull URL from Secrets
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet_url"]
except Exception:
    st.error("Missing 'spreadsheet_url' in Streamlit Secrets!")
    st.stop()

def load_wo_data():
    """Load Work Order data from the WO_Log tab"""
    data = conn.read(spreadsheet=SHEET_URL, worksheet="WO_Log", ttl=0)
    data.columns = [str(c).strip() for c in data.columns]
    return data

def load_user_list():
    """Load staff names from the 'users' tab with flexible naming"""
    try:
        user_data = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
        # Force all column headers to lowercase to avoid "name" vs "Name" errors
        user_data.columns = [str(c).strip().lower() for c in user_data.columns]
        
        if 'name' in user_data.columns:
            names = sorted(user_data['name'].dropna().unique().tolist())
            return [str(n) for n in names if str(n).strip() != ""]
        else:
            st.warning("Column 'name' not found in 'users' tab. Check your headers!")
            return ["Admin", "Unassigned"]
    except Exception as e:
        st.error(f"Could not read 'users' tab: {e}")
        return ["Admin", "Unassigned"]
)
st.title("📋 Karibu")

try:
    # Load Data
    df = load_wo_data()
    staff_options = load_user_list()
curr_assign = str(row['Assigned To']).strip()

# Safety: If current person isn't in the list, add them so the app doesn't crash
if curr_assign not in staff_options and curr_assign != 'nan' and curr_assign != "":
    staff_options.append(curr_assign)

# Calculate the index for the dropdown
try:
    staff_idx = staff_options.index(curr_assign)
except (ValueError, IndexError):
    staff_idx = 0

new_assignee = edit_col2.selectbox(
    "Reassign To", 
    options=staff_options, 
    index=staff_idx,
    help="Select a name from the 'users' sheet"
)

    # --- STATUS SUMMARY DASHBOARD ---
    st.subheader("📊 Status Overview")
    total_orders = len(df)
    pending = len(df[df['Status'] == 'Pending'])
    in_progress = len(df[df['Status'] == 'In Progress'])
    completed = len(df[df['Status'] == 'Completed'])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Orders", total_orders)
    m2.metric("Pending", pending)
    m3.metric("In Progress", in_progress)
    m4.metric("Completed", completed)
    
    st.divider()

    # --- SEARCH SECTION ---
    st.subheader("🔍 Search Work Order")
    search_query = st.text_input("Enter WO Number to Search", placeholder="e.g. 867")

    if search_query:
        # Match WO Number as string
        match = df[df['WO Number'].astype(str) == str(search_query)]

        if not match.empty:
            row = match.iloc[0]
            idx = match.index[0]

            st.success(f"Work Order #{search_query} Found!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Client:** {row['Client_Name_Display']}")
                st.write(f"**Phone:** {row['Client Phone']}")
            with col2:
                st.write(f"**Category:** {row['Category']}")
                st.write(f"**Subcategory:** {row['Subcategory']}")
            with col3:
                st.write(f"**Current Status:** {row['Status']}")
                st.write(f"**Current Assigned To:** {row['Assigned To']}")

            # --- EDIT SECTION ---
            st.markdown("### ✏️ Update Order")
            edit_col1, edit_col2 = st.columns(2)
            
            status_options = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"]
            
            # Status Selection
            curr_stat = str(row['Status']).strip()
            stat_idx = status_options.index(curr_stat) if curr_stat in status_options else 0
            new_status = edit_col1.selectbox("New Status", status_options, index=stat_idx)

            # Staff Selection (Ensuring we use Names, not Emails)
            curr_assign = str(row['Assigned To']).strip()
            
            # If the name currently in the sheet isn't in our 'users' list, add it as an option
            if curr_assign not in staff_options and curr_assign != 'nan':
                staff_options.append(curr_assign)
            
            try:
                staff_idx = staff_options.index(curr_assign)
            except:
                staff_idx = 0
                
            new_assignee = edit_col2.selectbox("Reassign To (Name)", staff_options, index=staff_idx)

            if st.button("Save Changes ✅", use_container_width=True):
                df.at[idx, 'Status'] = new_status
                df.at[idx, 'Assigned To'] = new_assignee
                conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df)
                st.success("Changes Saved!")
                st.rerun()
        else:
            st.error(f"WO #{search_query} not found.")

    # --- DATA PREVIEW (Cosmetic Update: No Index Column) ---
    st.divider()
    st.subheader("Recent Activity")
    
    # We use hide_index=True to remove that first column of numbers
    display_df = df[['WO Number', 'Date', 'Client_Name_Display', 'Status', 'Assigned To']].tail(10)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # --- ADMIN: ADD STAFF ---
    with st.expander("👤 Admin: Add New Staff Member"):
        st.info("Ensure the 'Name' provided here is what you want to appear in the dropdown.")
        with st.form("add_user", clear_on_submit=True):
            n_name = st.text_input("Staff Full Name")
            n_email = st.text_input("Staff Email")
            if st.form_submit_button("Add Staff"):
                if n_name:
                    u_df = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
                    new_u = pd.DataFrame([{"email": n_email, "name": n_name, "role": "Staff"}])
                    conn.update(spreadsheet=SHEET_URL, worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                    st.success(f"{n_name} added to staff list!")
                    st.rerun()

except Exception as e:
    st.error("An error occurred.")
    st.write(e)
