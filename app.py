
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- ACCESS CONTROL FUNCTION ---
def check_password():
    """Returns True if the user had the correct password."""
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔐 Karibu Private Access")
    
    # User input for password
    password_input = st.text_input("Enter Access Password", type="password")
    
    if st.button("Login"):
        if password_input == st.secrets.get("APP_PASSWORD", "mbuyu$1800"): # Fallback if secret is missing
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("🚫 Password incorrect")
            
    return False

# MUST be the first thing checked
if not check_password():
    st.stop()

# --- THE REST OF YOUR APP CODE STARTS HERE ---
# (Page Config, Connections, load_data, etc.)
st.set_page_config(page_title="Karibu Dashboard", layout="wide")
# ...

# Set page configuration
st.set_page_config(page_title="Karibu Task Manager", layout="wide")

# 1. Category System
CATEGORIES = {
    'PVC': ['CLEAR', 'PRC', 'UV', 'UVPC', 'CUT', 'PLN', 'GLDC', 'GLDP', 'ECO', 'CLRPRC', 'FRPL', 'FRCUT', 'FRPRC', 'MAG', 'RFL', 'HNY', 'UV CLEAR STICKER'],
    'EMB': ['STD', 'PRM'],
    'CAN': ['COT', 'UV', 'ECO', 'OTH'],
    'BAN': ['UV', 'ECO', 'TD', 'FECO', 'FUV', 'POP', 'STD', 'PRM', 'TELSCP', 'BKLUV', 'BACKLIGHT', 'BAN'],
    'MAP': ['NRM', 'PP', 'POP'],
    'SUB': ['SUB'],
    'DTF': ['DTF'],
    'CON': ['UV', 'ECO', 'PLN'],
    'FLT': ['UVD', 'PEN', 'NOTE', 'ACR'],
    'PUB': ['FLY', 'BR', 'BC', 'OTH'],
    'CUS': ['CUS', 'NFC-CRD']
}

# 2. Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Pull URL from Secrets
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet_url"]
except Exception:
    st.error("Missing 'spreadsheet_url' in Streamlit Secrets!")
    st.stop()

def load_sheet(name):
    try:
        data = conn.read(spreadsheet=SHEET_URL, worksheet=name, ttl=0)
        return data
    except:
        return pd.DataFrame()

st.title("📋 Karibu Work Order Manager")

try:
    # Load Data
    df_wo = load_sheet("WO_Log")
    df_clients = load_sheet("Clients")
    df_users = load_sheet("users")
    
    # Create search column for UI purposes
    if not df_wo.empty and 'WO Number' in df_wo.columns:
        df_wo['WO_SEARCH'] = df_wo['WO Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

    # --- SECTION 1: ADD NEW WORK ORDER ---
    with st.expander("➕ Create New Work Order", expanded=False):
        c_col1, c_col2 = st.columns(2)
        f_client_name = c_col1.text_input("Client Name").strip()
        f_phone = c_col2.text_input("Phone Number").strip()
        
        c_col3, c_col4, c_col5 = st.columns(3)
        f_cat = c_col3.selectbox("Category", options=[""] + sorted(list(CATEGORIES.keys())))
        sub_options = CATEGORIES.get(f_cat, []) if f_cat else []
        f_sub = c_col4.selectbox("Subcategory", options=sub_options)
        f_ver = c_col5.text_input("Version", value="V0")
        
        f_desc = st.text_area("Description").strip()
        
        if st.button("Generate & Save Work Order", type="primary"):
            if f_client_name and f_cat and f_sub:
                # --- A. CLIENT TAB LOGIC ---
                client_id = ""
                if not df_clients.empty and 'Client Name' in df_clients.columns:
                    existing = df_clients[df_clients['Client Name'].str.upper() == f_client_name.upper()]
                else:
                    existing = pd.DataFrame()
                
                if not existing.empty:
                    client_id = str(existing.iloc[0]['ClientID'])
                else:
                    try:
                        c_nums = pd.to_numeric(df_clients['ClientID'].str.replace('C-', ''), errors='coerce')
                        next_c = int(c_nums.max()) + 1 if not pd.isna(c_nums.max()) else 1001
                    except:
                        next_c = 1001
                    client_id = f"C-{next_c}"
                    
                    new_client_row = pd.DataFrame([{
                        "ClientID": client_id,
                        "Client Name": f_client_name.upper(),
                        "Phone": f_phone,
                        "Active": "TRUE"
                    }])
                    df_clients = pd.concat([df_clients, new_client_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Clients", data=df_clients)

                # --- B. WO_LOG LOGIC ---
                try:
                    nums = pd.to_numeric(df_wo['WO Number'], errors='coerce')
                    new_wo_num = int(nums.max()) + 1 if not pd.isna(nums.max()) else 1001
                except:
                    new_wo_num = 1001
                
                now = datetime.now()
                iso_date = now.strftime("%Y-%m-%d")
                short_date = now.strftime("%d%m%y")
                
                filename = f"WO{str(new_wo_num).zfill(3)}_{short_date}_{f_cat}-{f_sub}_{f_client_name}_{f_desc}_{f_ver}".upper().replace(" ", "_")
                
                # EXACT HEADER MAPPING
                new_wo_data = {
                    "WO Number": str(new_wo_num),           # A
                    "Date": iso_date,                      # B
                    "Category": f_cat,                     # C
                    "Subcategory": f_sub,                  # D
                    "Client": client_id,                   # E (ClientID recorded here)
                    "Client Phone": f_phone,               # F (Phone recorded here)
                    "Description": f_desc.upper(),         # G
                    "Version": f_ver.upper(),              # H
                    "Full Filename": filename,             # I
                    "Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), # J
                    "Status": "Pending",                   # K
                    "Client_Name_Display": f_client_name.upper(), # M
                    "Assigned To": "Unassigned"            # N
                }
                
                new_wo_row = pd.DataFrame([new_wo_data])
                
                # Append and clean up temp search column before upload
                df_wo = pd.concat([df_wo, new_wo_row], ignore_index=True)
                if 'WO_SEARCH' in df_wo.columns:
                    df_wo = df_wo.drop(columns=['WO_SEARCH'])

                conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df_wo)
                st.success(f"WO #{new_wo_num} Created!")
                st.rerun()
            else:
                st.error("Please fill in Client Name, Category, and Subcategory.")

    # --- SECTION 2: SEARCH & EDIT ---
    st.subheader("🔍 Search & Update")
    search_query = st.text_input("Search by WO Number").strip().upper()

    if search_query and not df_wo.empty:
        match = df_wo[df_wo['WO_SEARCH'] == search_query]
        if not match.empty:
            row = match.iloc[0]
            idx = match.index[0]
            with st.container(border=True):
                st.write(f"### Editing WO #{search_query}")
                st.caption(f"**Filename:** {row.get('Full Filename', 'N/A')}")
                
                e_col1, e_col2 = st.columns(2)
                status_list = ["Pending", "In progress", "Completed", "On Hold", "Cancelled"]
                curr_s = str(row['Status']).strip()
                try:
                    s_idx = [s.lower() for s in status_list].index(curr_s.lower())
                except:
                    s_idx = 0
                new_status = e_col1.selectbox("Status", status_list, index=s_idx)

                # User list
                users = []
                if not df_users.empty:
                    u_cols = [c.strip().lower() for c in df_users.columns]
                    if 'name' in u_cols:
                        name_col = df_users.columns[u_cols.index('name')]
                        users = sorted(df_users[name_col].dropna().unique().tolist())
                
                drop_opts = sorted(list(set(["Admin", "Unassigned"] + users)))
                curr_a = str(row['Assigned To']).strip()
                if curr_a not in drop_opts and curr_a.lower() != 'nan' and curr_a != "":
                    drop_opts.append(curr_a)
                try:
                    a_idx = drop_opts.index(curr_a)
                except:
                    a_idx = 0
                new_assignee = e_col2.selectbox("Assigned To", drop_opts, index=a_idx)

                if st.button("Save Changes ✅"):
                    df_wo.at[idx, 'Status'] = new_status
                    df_wo.at[idx, 'Assigned To'] = new_assignee
                    
                    if 'WO_SEARCH' in df_wo.columns:
                        df_wo = df_wo.drop(columns=['WO_SEARCH'])
                        
                    conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df_wo)
                    st.success("Updated!")
                    st.rerun()

    # --- UPDATED SECTION: ACTIVE TASKS / OPERATOR PANEL ---
    st.divider()
    st.subheader("🚀 Active Tasks")

if not df_wo.empty:
    # 1. Standardize column names (removes hidden spaces)
    df_wo.columns = [str(c).strip() for c in df_wo.columns]
    
    # 2. Find the correct column for "Assigned To Name"
    # This looks for any header that contains "Assigned" or "Name"
    staff_col = next((c for c in df_wo.columns if 'Assigned' in c or 'Name' in c and c != 'Client Name'), "Assigned To Name")

    # 3. Prepare display dataframe
    df_wo['Status'] = df_wo['Status'].astype(str)
    
    # Filter for active tasks
    active_mask = (df_wo['Status'].str.lower().isin(['pending', 'in progress']))
    final_view = df_wo[active_mask].copy()

    # 4. Ensure the column is rendered correctly
    # Select specific columns to show, using the dynamically found staff_col
    cols_to_show = ['WO Number', 'Date', 'Category', 'Subcategory', 'Full Filename', staff_col, 'Status']
    
    # Only use columns that actually exist to prevent errors
    existing_cols = [c for c in cols_to_show if c in final_view.columns]

    if not final_view.empty:
        st.dataframe(
            final_view[existing_cols], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No active tasks found.")
