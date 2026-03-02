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
