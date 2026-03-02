import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Set page configuration
st.set_page_config(page_title="Karibu Task Manager", layout="wide")

# 1. Complete Category & Subcategory System
CATEGORIES = {
    'PVC': ['CLEAR', 'PRC', 'UV', 'UVPC', 'CUT', 'PLN', 'GLDC', 'GLDP', 'ECO', 'CLRPRC', 'FRPL', 'FRCUT', 'FRPRC', 'MAG', 'RFL', 'HNY', 'UV CLEAR STICKER'],
    'EMB': ['STD', 'PRM'],
    'CAN': ['COT', 'UV', 'ECO', 'OTH'],
    'BAN': ['UV', 'ECO', 'TD', 'FECO', 'FUV', 'POP', 'STD', 'PRM', 'TELSCP', 'BKLUV', 'BACKLIGHT'],
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

def load_wo_data():
    try:
        data = conn.read(spreadsheet=SHEET_URL, worksheet="WO_Log", ttl=0)
        data.columns = [str(c).strip() for c in data.columns]
        if 'WO Number' in data.columns:
            data['WO Number'] = data['WO Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
        return data
    except:
        return pd.DataFrame()

def load_user_list():
    try:
        user_data = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
        user_data.columns = [str(c).strip().lower() for c in user_data.columns]
        if 'name' in user_data.columns:
            return sorted(user_data['name'].dropna().astype(str).str.strip().unique().tolist())
        return []
    except:
        return []

st.title("📋 Karibu Work Order Manager")

try:
    df = load_wo_data()
    staff_names = load_user_list()

    # --- SECTION 1: ADD NEW WORK ORDER ---
    with st.expander("➕ Create New Work Order", expanded=False):
        # NOTE: Fields are outside the form for immediate reactivity, 
        # then we use a standard button to save.
        c_col1, c_col2 = st.columns(2)
        f_client = c_col1.text_input("Client Name", key="nc_client").strip()
        f_phone = c_col2.text_input("Phone Number", key="nc_phone").strip()
        
        c_col3, c_col4, c_col5 = st.columns(3)
        f_cat = c_col3.selectbox("Category", options=[""] + sorted(list(CATEGORIES.keys())), key="nc_cat")
        
        # This list now updates immediately when Category changes
        sub_options = CATEGORIES.get(f_cat, []) if f_cat else []
        f_sub = c_col4.selectbox("Subcategory", options=sub_options, key="nc_sub")
        
        f_ver = c_col5.text_input("Version", value="V0", key="nc_ver")
        f_desc = st.text_area("Description", key="nc_desc").strip()
        
        if st.button("Generate & Save Work Order", type="primary"):
            if f_client and f_cat and f_sub:
                # Calculate Next WO Number
                try:
                    nums = pd.to_numeric(df['WO Number'], errors='coerce')
                    new_wo_num = int(nums.max()) + 1 if not pd.isna(nums.max()) else 1001
                except:
                    new_wo_num = 1001
                
                now = datetime.now()
                iso_date = now.strftime("%Y-%m-%d")
                short_date = now.strftime("%d%m%y")
                
                filename = f"WO{str(new_wo_num).zfill(3)}_{short_date}_{f_cat}-{f_sub}_{f_client}_{f_desc}_{f_ver}".upper().replace(" ", "_")
                
                new_row = pd.DataFrame([{
                    "WO Number": str(new_wo_num),
                    "Date": iso_date,
                    "Category": f_cat,
                    "Subcategory": f_sub,
                    "Client_Name_Display": f_client.upper(),
                    "Client Phone": f_phone,
                    "Description": f_desc.upper(),
                    "Version": f_ver.upper(),
                    "Filename": filename,
                    "Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "Status": "Pending",
                    "Assigned To": "Unassigned"
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=updated_df)
                st.success(f"Work Order #{new_wo_num} Created!")
                st.rerun()
            else:
                st.error("Please provide Client, Category, and Subcategory.")

    # --- SECTION 2: SEARCH & EDIT ---
    st.subheader("🔍 Search & Update")
    search_query = st.text_input("Search by WO Number").strip().upper()

    if search_query:
        match = df[df['WO Number'] == search_query]
        if not match.empty:
            row = match.iloc[0]
            idx = match.index[0]
            with st.container(border=True):
                st.write(f"### Editing WO #{search_query}")
                st.caption(f"**Filename:** {row.get('Filename', 'N/A')}")
                
                e_col1, e_col2 = st.columns(2)
                status_list = ["Pending", "In progress", "Completed", "On Hold", "Cancelled"]
                curr_s = str(row['Status']).strip()
                try:
                    s_idx = [s.lower() for s in status_list].index(curr_s.lower())
                except:
                    s_idx = 0
                new_status = e_col1.selectbox("Status", status_list, index=s_idx)

                drop_opts = sorted(list(set(["Admin", "Unassigned"] + staff_names)))
                curr_a = str(row['Assigned To']).strip()
                if curr_a not in drop_opts and curr_a.lower() != 'nan' and curr_a != "":
                    drop_opts.append(curr_a)
                try:
                    a_idx = drop_opts.index(curr_a)
                except:
                    a_idx = 0
                new_assignee = e_col2.selectbox("Assigned To", drop_opts, index=a_idx)

                if st.button("Save Changes ✅", key="save_edit"):
                    df.at[idx, 'Status'] = new_status
                    df.at[idx, 'Assigned To'] = new_assignee
                    conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df)
                    st.success("Updated!")
                    st.rerun()

    # --- SECTION 3: ACTIVE TASKS ---
    st.divider()
    st.subheader("🚀 Active Tasks")
    
    df['Status'] = df['Status'].astype(str)
    df['Assigned To'] = df['Assigned To'].astype(str)

    active_mask = (df['Status'].str.lower().isin(['pending', 'in progress'])) | \
                  (df['Assigned To'].str.lower().isin(['nan', 'unassigned', '']))
    
    final_view = df[active_mask]
    final_view = final_view[~final_view['Status'].str.lower().isin(['completed', 'cancelled'])]

    if not final_view.empty:
        st.dataframe(final_view[['WO Number', 'Date', 'Client_Name_Display', 'Status', 'Assigned To']], use_container_width=True, hide_index=True)
    else:
        st.info("No active tasks.")

except Exception as e:
    st.error(f"Application Error: {e}")
