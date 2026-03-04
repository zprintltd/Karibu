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
        if password_input == st.secrets.get("APP_PASSWORD", "Admin123"): # Fallback if secret is missing
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


# 1. Page Config
st.set_page_config(page_title="Karibu Performance Dashboard", layout="wide")

# 2. Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Fetch and clean data with specific fixes for empty subcategories"""
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet_url"]
    except Exception:
        st.error("Missing GSheets URL in Secrets!")
        st.stop()

    df = conn.read(spreadsheet=url, worksheet="WO_Log", ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Handle Dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Standardize Status
    df['Status_Lower'] = df['Status'].astype(str).str.lower().str.strip()

    # FIX FOR TREEMAP ERROR: Fill empty Category or Subcategory
    df['Category'] = df['Category'].astype(str).replace(['', 'nan', 'None', ' '], 'UNCATEGORIZED')
    df['Subcategory'] = df['Subcategory'].astype(str).replace(['', 'nan', 'None', ' '], 'GENERAL')

    # Handle Staff/Assigned To
    assigned_col = next((c for c in df.columns if 'Assigned' in c), None)
    if assigned_col:
        df['Staff_Display'] = df[assigned_col].astype(str).replace(['', 'nan', 'None', ' '], 'Unassigned')
        df['Staff_Lower'] = df['Staff_Display'].str.lower()
    else:
        df['Staff_Display'] = 'Unassigned'
        df['Staff_Lower'] = 'unassigned'
        
    return df

# --- MAIN APP LOGIC ---
try:
    df = load_data()
    
    today = datetime.now().date()
    this_month = datetime.now().month
    this_year = datetime.now().year

    st.title("📊 Karibu Operations Dashboard")
    st.markdown(f"**Refresh Date:** {datetime.now().strftime('%d %b %Y | %H:%M')}")

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
        status_count = df['Status'].value_counts().reset_index()
        fig_pie = px.pie(status_count, values='count', names='Status', hole=0.5)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("📅 Monthly Completion Goal")
        month_df = df[(df['Date'].dt.month == this_month) & (df['Date'].dt.year == this_year)]
        monthly_comp = len(month_df[month_df['Status_Lower'] == 'completed'])
        target = 100 
        progress_val = min(monthly_comp / target, 1.0)
        st.write(f"Completed this month: **{monthly_comp}**")
        st.progress(progress_val)
        
        unassigned_count = len(df[df['Staff_Lower'].isin(['nan', 'unassigned', '', 'none'])])
        if unassigned_count > 0:
            st.warning(f"⚠️ {unassigned_count} tasks are currently unassigned.")

    st.divider()

    # --- YTD ANALYSIS ---
    st.subheader("📈 Year-To-Date (YTD) Activity")
    completed_ytd = df[(df['Date'].dt.year == this_year) & (df['Status_Lower'] == 'completed')]

    if not completed_ytd.empty:
        plot_df = completed_ytd.copy()
        
        # Prevent Parent/Child name collision
        plot_df.loc[plot_df['Category'] == plot_df['Subcategory'], 'Subcategory'] = plot_df['Subcategory'] + " "
        
        try:
            fig_tree = px.treemap(
                plot_df, 
                path=[px.Constant("All Work"), 'Category', 'Subcategory'],
                color='Category',
                title="Completed Categories Hierarchy (YTD)",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )

            # --- CLEAN LABELS & EXTRA LARGE FONT ---
            # IMPORTANT: No spaces between % and {
            fig_tree.update_traces(
                textinfo="label+value",
                texttemplate="<span style='font-size:30px'><b>%{label}</b></span><br><span style='font-size:26px'>%{value}</span>",
                hovertemplate="<b>%{label}</b><br>Total: %{value}",
                textposition="middle center"
            )
            
            # Layout adjustments for visibility
            fig_tree.update_layout(
                margin=dict(t=50, l=10, r=10, b=10),
                # uniformtext forces the font to stay large and not shrink for small boxes
                uniformtext=dict(minsize=18, mode='hide') 
            )
            
            st.plotly_chart(fig_tree, use_container_width=True)
            
        except Exception as tree_err:
            st.warning("Switching to bar chart due to data structure issues.")
            st.bar_chart(completed_ytd['Category'].value_counts())
    else:
        st.info("No completed data for YTD.")

    # --- STAFF PERFORMANCE ---
    st.divider()
    st.subheader("👤 Staff Leaderboard (Monthly)")
    if not month_df.empty:
        staff_perf = month_df[month_df['Status_Lower'] == 'completed']['Staff_Display'].value_counts().reset_index()
        if not staff_perf.empty:
            fig_staff = px.bar(staff_perf, x='Staff_Display', y='count', 
                               color='count', color_continuous_scale='Greens')
            st.plotly_chart(fig_staff, use_container_width=True)
        else:
            st.write("No completions by staff this month.")

except Exception as e:
    st.error(f"Critical Error: {e}")
