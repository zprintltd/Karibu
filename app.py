import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

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
        data.columns = [str(c).strip() for c in data.columns]
        return data
    except:
        return pd.DataFrame()

st.title("📋 Karibu Work Order Manager")

try:
    # Load Data
    df_wo = load_sheet("WO_Log")
    df_clients = load_sheet("Clients")
    staff_names = load_sheet("users")
    
    # Process WO numbers for searching
    if not df_wo.empty and 'WO Number' in df_wo.columns:
        df_wo['WO Number'] = df_wo['WO Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

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
                # A. Handle Client Logic (Tab: Clients)
                client_id = ""
                # Search for existing client
                existing = df_clients[df_clients['Client Name'].str.upper() == f_client_name.upper()] if not df_clients.empty else pd.DataFrame()
                
                if not existing.empty:
                    client_id = existing.iloc[0]['ClientID']
                else:
                    # Create New Client
                    try:
                        # Extract number from C-1001 pattern
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

                # B. Handle WO Logic (Tab: WO_Log)
                try:
                    nums = pd.to_numeric(df_wo['WO Number'], errors='coerce')
                    new_wo_num = int(nums.max()) + 1 if not pd.isna(nums.max()) else 1001
                except:
                    new_wo_num = 1001
                
                now = datetime.now()
                iso_date = now.strftime("%Y-%m-%d")
                short_date = now.strftime("%d%m%y")
                
                filename = f"WO{str(new_wo_num).zfill(3)}_{short_date}_{f_cat}-{f_sub}_{f_client_name}_{f_desc}_{f_ver}".upper().replace(" ", "_")
                
                # Create the New WO Row using your specific column naming/positions
                new_wo_row = pd.DataFrame([{
                    "WO Number": str(new_wo_num),           # Col A
                    "Date": iso_date,                      # Col B
                    "Category": f_cat,                     # Col C
                    "Subcategory": f_sub,                  # Col D
                    "ClientID": client_id,                 # Col E
                    "Phone": f_phone,                      # Col F (Assuming Col F is phone)
                    "Description": f_desc.upper(),         # Col G
                    "Version": f_ver.upper(),              # Col H
                    "Full Filename": filename,             # Col I (FIXED)
                    "Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Pending",
                    "Client_Name_Display": f_client_name.upper(), # Col M (FIXED)
                    "Assigned To": "Unassigned"
                }])
                
                df_wo = pd.concat([df_wo, new_wo_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df_wo)
                st.success(f"WO #{new_wo_num} Created for {f_client_name}!")
                st.rerun()
            else:
                st.error("Please provide Client Name, Category, and Subcategory.")

    # --- SECTION 2: SEARCH & EDIT ---
    st.subheader("🔍 Search & Update")
    search_query = st.text_input("Search by WO Number").strip().upper()

    if search_query and not df_wo.empty:
        match = df_wo[df_wo['WO Number'] == search_query]
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

                # Prep user list
                users = []
                if not staff_names.empty:
                    staff_names.columns = [c.lower() for c in staff_names.columns]
                    if 'name' in staff_names.columns:
                        users = sorted(staff_names['name'].dropna().unique().tolist())
                
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
                    conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df_wo)
                    st.success("Updated!")
                    st.rerun()

    # --- SECTION 3: ACTIVE TASKS ---
    st.divider()
    st.subheader("🚀 Active Tasks")
    if not df_wo.empty:
        df_wo['Status'] = df_wo['Status'].astype(str)
        df_wo['Assigned To'] = df_wo['Assigned To'].astype(str)

        active_mask = (df_wo['Status'].str.lower().isin(['pending', 'in progress'])) | \
                      (df_wo['Assigned To'].str.lower().isin(['nan', 'unassigned', '']))
        
        final_view = df_wo[active_mask]
        final_view = final_view[~final_view['Status'].str.lower().isin(['completed', 'cancelled'])]

        if not final_view.empty:
            st.dataframe(final_view[['WO Number', 'Date', 'Client_Name_Display', 'Status', 'Assigned To']], use_container_width=True, hide_index=True)
        else:
            st.info("No active tasks.")

except Exception as e:
    st.error(f"Application Error: {e}")
