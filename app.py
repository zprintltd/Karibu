import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

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
    data = conn.read(spreadsheet=SHEET_URL, worksheet="WO_Log", ttl=0)
    data.columns = [str(c).strip() for c in data.columns]
    return data

def load_user_list():
    try:
        user_data = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
        user_data.columns = [str(c).strip().lower() for c in user_data.columns]
        if 'name' in user_data.columns:
            return sorted(user_data['name'].dropna().unique().tolist())
        return ["Admin", "Unassigned"]
    except:
        return ["Admin", "Unassigned"]

st.title("📋 Karibu Work Order Manager")

try:
    df = load_wo_data()
    staff_options = load_user_list()

    # --- DASHBOARD ---
    st.subheader("📊 Status Overview")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", len(df))
    m2.metric("Pending", len(df[df['Status'] == 'Pending']))
    m3.metric("In Progress", len(df[df['Status'] == 'In Progress']))
    m4.metric("Completed", len(df[df['Status'] == 'Completed']))
    st.divider()

    # --- SEARCH & EDIT ---
    st.subheader("🔍 Search & Update Order")
    search_query = st.text_input("Enter WO Number", placeholder="Type WO number and press Enter")

    if search_query:
        match = df[df['WO Number'].astype(str) == str(search_query)]

        if not match.empty:
            row = match.iloc[0]
            idx = match.index[0]

            # Display info in a nice box
            with st.container(border=True):
                st.write(f"### Work Order #{search_query}")
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Client:** {row['Client_Name_Display']}")
                c2.write(f"**Category:** {row['Category']}")
                c3.write(f"**Description:** {row['Description']}")
                
                st.markdown("---")
                st.write("#### ✏️ Edit Assignment & Status")
                
                edit_col1, edit_col2 = st.columns(2)
                
                # Status Dropdown
                status_list = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"]
                curr_s = str(row['Status']).strip()
                s_idx = status_list.index(curr_s) if curr_s in status_list else 0
                new_status = edit_col1.selectbox("Set Status", status_list, index=s_idx)

                # Staff Dropdown
                curr_a = str(row['Assigned To']).strip()
                if curr_a not in staff_options and curr_a != 'nan' and curr_a != "":
                    staff_options.append(curr_a)
                
                try:
                    a_idx = staff_options.index(curr_a)
                except:
                    a_idx = 0
                
                new_assignee = edit_col2.selectbox("Assigned To", staff_options, index=a_idx)

                # SAVE BUTTON
                if st.button("Save Changes ✅", use_container_width=True, type="primary"):
                    df.at[idx, 'Status'] = new_status
                    df.at[idx, 'Assigned To'] = new_assignee
                    conn.update(spreadsheet=SHEET_URL, worksheet="WO_Log", data=df)
                    st.success("Work Order Updated!")
                    st.rerun()
        else:
            st.error("Work Order not found.")

    # --- TABLE ---
    st.divider()
    st.subheader("Recent Activity")
    st.dataframe(df[['WO Number', 'Date', 'Client_Name_Display', 'Status', 'Assigned To']].tail(15), 
                 use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Error connecting to data.")
    st.write(e)
