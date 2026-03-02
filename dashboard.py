import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# Page configuration for a professional look
st.set_page_config(page_title="Karibu Performance Dashboard", layout="wide")

# 1. Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Fetch and clean data for analysis"""
    df = conn.read(worksheet="WO_Log", ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Convert dates to datetime objects for time-based filtering
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    
    # Standardize Status and Assigned To
    df['Status_Lower'] = df['Status'].astype(str).str.lower().str.strip()
    df['Staff_Lower'] = df['Assigned To'].astype(str).str.lower().str.strip()
    return df

try:
    df = load_data()
    
    # Current Time Logic
    today = datetime.now().date()
    this_month = datetime.now().month
    this_year = datetime.now().year

    st.title("📊 Karibu Operations Dashboard")
    st.markdown(f"**Data Refresh:** {datetime.now().strftime('%d %b %Y | %H:%M')}")

    # --- KPI METRICS TOP ROW ---
    # 1. Today's New Tasks
    new_today = df[df['Date'].dt.date == today]
    
    # 2. Completed Today
    comp_today = df[(df['Date'].dt.date == today) & (df['Status_Lower'] == 'completed')]
    
    # 3. Currently Progressing
    in_progress = df[df['Status_Lower'] == 'in progress']
    
    # 4. Currently Pending
    pending = df[df['Status_Lower'] == 'pending']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tasks Created Today", len(new_today))
    m2.metric("Completed Today", len(comp_today))
    m3.metric("Currently In Progress", len(in_progress))
    m4.metric("Total Pending (Backlog)", len(pending))

    st.divider()

    # --- MIDDLE SECTION: PIE & MONTHLY PROGRESS ---
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📋 Overall Work Status")
        status_count = df['Status'].value_counts().reset_index()
        fig_pie = px.pie(status_count, values='count', names='Status', 
                         hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("📅 Completed This Month")
        month_df = df[(df['Date'].dt.month == this_month) & (df['Date'].dt.year == this_year)]
        monthly_comp = len(month_df[month_df['Status_Lower'] == 'completed'])
        
        # Monthly Goal tracking (Set target to 100 or any number)
        target = 100 
        progress_val = min(monthly_comp / target, 1.0)
        
        st.write(f"Total Completed: **{monthly_comp}**")
        st.progress(progress_val)
        st.write(f"Goal Progress: {int(progress_val*100)}% of {target} target")
        
        # KPI: Unassigned Alert
        unassigned_count = len(df[df['Staff_Lower'].isin(['nan', 'unassigned', ''])])
        if unassigned_count > 0:
            st.warning(f"⚠️ Warning: {unassigned_count} tasks are currently unassigned.")

    st.divider()

    # --- YTD ANALYSIS SECTION ---
    st.subheader("📈 Year-To-Date (YTD) Activity")
    ytd_data = df[df['Date'].dt.year == this_year]
    
    if not ytd_data.empty:
        # Hierarchy chart: Category > Subcategory
        st.write("**Category & Subcategory Volume (Completed Work)**")
        completed_ytd = ytd_data[ytd_data['Status_Lower'] == 'completed']
        
        if not completed_ytd.empty:
            fig_tree = px.treemap(completed_ytd, path=['Category', 'Subcategory'], 
                                  title="Completed Categories Hierarchy")
            st.plotly_chart(fig_tree, use_container_width=True)
            
            # Bar Chart: Monthly Completions across the Year
            st.write("**Completions by Month**")
            monthly_trend = completed_ytd.groupby(completed_ytd['Date'].dt.strftime('%B')).size().reindex([
                'January', 'February', 'March', 'April', 'May', 'June', 
                'July', 'August', 'September', 'October', 'November', 'December'
            ]).reset_index(name='Completions')
            fig_line = px.line(monthly_trend.dropna(), x='Date', y='Completions', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No tasks have been marked as 'Completed' YTD.")
    else:
        st.info("No data found for the current year.")

except Exception as e:
    st.error("Dashboard Load Error")
    st.write(f"Details: {e}")
