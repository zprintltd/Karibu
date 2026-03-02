import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

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
    data = conn.read(spreadsheet=SHEET_URL, worksheet="WO_Log", ttl=0)
    data.columns = [str(c).strip() for c in data.columns]
    if 'WO Number' in data.columns:
        # Keep internal WO Number as string for matching
        data['WO Number'] = data['WO Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
    return data

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
        with st.form("new_wo_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_client = col1.text_input("Client Name")
            f_phone = col2.text_input("Phone Number")
            
            col3, col4, col5 = st.columns(3)
            f_cat = col3.text_input("Category (e.g., PLUMBING)")
            f_sub = col4.text_input("Subcategory")
            f_ver = col5.text_input("Version", value="V0")
            
            f_desc = st.text_area("Description")
            
            if st.form_submit_button("Generate & Save Work Order"):
                if f_client and f_cat:
                    # Calculate Next WO Number
                    try:
                        last_wo = pd.to_numeric(df['WO Number'], errors='coerce').max()
                        new_wo_num = int(last_wo) + 1 if not pd.isna(last_wo) else 1
                    except:
                        new_wo_num = 1
                    
                    # Formatting Date per your script logic (DDMMYY)
                    now = datetime.now()
                    iso_date = now.strftime("%Y-%m-%d")
                    short_date = now.strftime("%d%m%y")
                    
                    # Generate Filename (All Caps)
                    # Format: WO001_DDMMYY_CAT-SUB_CLIENT_DESC_V0
                    filename = (
                        f"WO{str(new_wo_num).zfill(3)}_{short_date}_"
                        f"{f_cat}-{f_sub}_{f_client}_{f_desc}_{f_ver}"
                    ).upper().replace(" ", "_") # Cleanup spaces for filename
                    
                    # Prepare New Row (Matching your Google Sheet column order)
                    new_row = pd.DataFrame([{
                        "WO Number": str(new_wo_num),
                        "Date": iso_date,
                        "Category": f_cat.upper(),
                        "Subcategory": f_sub.upper(),
                        "Client_Name_Display": f_client.upper(), # Adjust column name if needed
                        "Client Phone": f_phone,
                        "Description": f_desc.upper(),
                        "Version": f_ver.upper(),
                        "Filename": filename,
                        "Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "Status": "Pending",
                        "Assigned To": "Unassigned"
                    }])
                    
                    # Update Google Sheets
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=updated_df)
                    
                    st.success(f"Created WO #{new_wo_num} | Filename: {filename}")
                    st.rerun()
                else:
                    st.warning("Please fill in at least Client and Category.")

    # --- SECTION 2: SEARCH & EDIT ---
    st.subheader("🔍 Search & Update")
    search_query = st.text_input("Enter WO Number to Search").strip().upper()

    if search_query:
        match = df[df['WO Number'] == search_query]
        if not match.empty:
            row = match.iloc[0]
            idx = match.index[0]
            with st.container(border=True):
                st.write(f"### Editing WO #{search_query}")
                st.info(f"**Filename:** {row.get('Filename', 'N/A')}")
                
                edit_col1, edit_col2 = st.columns(2)
                
                # Status Dropdown
                status_list = ["Pending", "In progress", "Completed", "On Hold", "Cancelled"]
                curr_s = str(row['Status']).strip()
                try:
                    s_idx = [s.lower() for s in status_list].index(curr_s.lower())
                except:
                    s_idx = 0
                new_status = edit_col1.selectbox("Status", status_list, index=s_idx)

                # Staff Dropdown
                drop_opts = sorted(list(set(["Admin", "Unassigned"] + staff_names)))
                curr_a = str(row['Assigned To']).strip()
                if curr_a not in drop_opts and curr_a.lower() != 'nan' and curr_a != "":
                    drop_opts.append(curr_a)
                try:
                    a_idx = drop_opts.index(curr_a)
                except:
                    a_idx = 0
                new_assignee = edit_col2.selectbox("Assigned To", drop_opts, index=a_idx)

                if st.button("Save Changes ✅", use_container_width=True, type="primary"):
                    df.at[idx, 'Status'] = new_status
                    df.at[idx, 'Assigned To'] = new_assignee
                    conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df)
                    st.success("Updated!")
                    st.rerun()

    # --- SECTION 3: ACTIVE TASKS TABLE ---
    st.divider()
    st.subheader("🚀 Active Tasks")
    # Filters
    active_mask = (
        (df['Status'].str.lower().isin(['pending', 'in progress'])) |
        (df['Assigned To'].str.lower().isin(['nan', 'unassigned', '']))
    )
    final_view = df[active_mask]
    final_view = final_view[~final_view['Status'].str.lower().isin(['completed', 'cancelled'])]

    if not final_view.empty:
        st.dataframe(
            final_view[['WO Number', 'Date', 'Client_Name_Display', 'Status', 'Assigned To']], 
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No active tasks.")

except Exception as e:
    st.error(f"Application Error: {e}")
