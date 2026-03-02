import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Karibu Performance Dashboard", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Fetch and clean data for analysis with robust column finding"""
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet_url"]
    except Exception:
        st.error("Missing GSheets URL in Secrets!")
        st.stop()

    df = conn.read(spreadsheet=url, worksheet="WO_Log", ttl=0)
    # Clean headers
    df.columns = [str(c).strip() for c in df.columns]
    
    # 1. Handle Dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # 2. Standardize Status
    if 'Status' in df.columns:
        df['Status_Lower'] = df['Status'].astype(str).str.lower().str.strip()
    else:
        df['Status_Lower'] = "unknown"

    # 3. Handle 'Assigned To' (The column causing the error)
    # We look for a column that contains 'Assigned' just in case of typos
    assigned_col = next((c for c in df.columns if 'Assigned' in c), None)
    
    if assigned_col:
        df['Staff_Lower'] = df[assigned_col].astype(str).str.lower().str.strip()
        # Create a clean display version for charts
        df['Staff_Display'] = df[assigned_col].fillna("Unassigned")
    else:
        df['Staff_Lower'] = "unassigned"
        df['Staff_Display'] = "Unassigned"
        
    return df

try:
    df = load_data()
    
    today = datetime.now().date()
    this_month = datetime.now().month
    this_year = datetime.now().year

    st.title("📊 Karibu Operations Dashboard")

    # --- KPI METRICS ---
    new_today = df[df['Date'].dt.date == today]
    comp_today = df[(df['Date'].dt.date == today) & (df['Status_Lower'] == 'completed')]
    in_progress = df[df['Status_Lower'] == 'in progress']
    pending = df[df['Status_Lower'] == 'pending']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tasks Created Today", len(new_today))
    m2.metric("Completed Today", len(comp_today))
    m3.metric("Currently In Progress", len(in_progress))
    m4.metric("Total Pending (Backlog)", len(pending))

    st.divider()

    # --- STATUS PIE & PROGRESS ---
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📋 Overall Work Status")
        if 'Status' in df.columns:
            status_count = df['Status'].value_counts().reset_index()
            fig_pie = px.pie(status_count, values='count', names='Status', hole=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("📅 Monthly Completion Goal")
        month_df = df[(df['Date'].dt.month == this_month) & (df['Date'].dt.year == this_year)]
        monthly_comp = len(month_df[month_df['Status_Lower'] == 'completed'])
        target = 100 
        progress_val = min(monthly_comp / target, 1.0)
        st.write(f"Completed: **{monthly_comp}**")
        st.progress(progress_val)
        
        # KPI: Unassigned Alert
        unassigned_count = len(df[df['Staff_Lower'].isin(['nan', 'unassigned', '','none'])])
        if unassigned_count > 0:
            st.warning(f"⚠️ {unassigned_count} tasks are currently unassigned.")

    st.divider()

    # --- YTD ANALYSIS ---
    st.subheader("📈 Year-To-Date (YTD) Activity")
    completed_ytd = df[(df['Date'].dt.year == this_year) & (df['Status_Lower'] == 'completed')]
    
    if not completed_ytd.empty:
        fig_tree = px.treemap(completed_ytd, path=['Category', 'Subcategory'], 
                              title="Completed Categories Hierarchy")
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("No completed data for YTD.")

    # --- STAFF PERFORMANCE ---
    st.divider()
    st.subheader("👤 Staff Leaderboard (Monthly)")
    if not month_df.empty:
        # Count completions by staff
        staff_perf = month_df[month_df['Status_Lower'] == 'completed']['Staff_Display'].value_counts().reset_index()
        if not staff_perf.empty:
            fig_staff = px.bar(staff_perf, x='Staff_Display', y='count', 
                               labels={'Staff_Display': 'Employee', 'count': 'Tasks Completed'},
                               color='count', color_continuous_scale='Greens')
            st.plotly_chart(fig_staff, use_container_width=True)
        else:
            st.write("No completions recorded by staff this month.")

except Exception as e:
    st.error(f"Dashboard Error: {e}")
