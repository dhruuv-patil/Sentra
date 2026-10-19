import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px
from core.config import config
from core.crypto import crypto
from data.database import Database
from app.dashboard.ui_components import inject_custom_css

def run_dashboard():
    st.set_page_config(page_title="LLM Gateway | Security Dashboard", layout="wide", page_icon="🛡️")
    inject_custom_css()

    # Sidebar Navigation
    with st.sidebar:
        st.image("https://img.icons8.com/parakeet/96/shield.png", width=80)
        st.markdown("<h2 style='color: white; margin-bottom: 20px;'>Gateway Admin</h2>", unsafe_allow_html=True)
        page = st.radio("MAIN MENU", ["🚀 Overview", "⚖️ Approvals", "📈 Analytics", "📜 History", "🛡️ Security"])
        st.divider()
        st.markdown("### System Status")
        st.success("Backend: Online")
        st.info(f"Host: {config.API_HOST}")
        st.divider()
        st.markdown("👨‍💻 **Author:** [Dhruv Patil](https://github.com/dhruuv-patil)")
        st.markdown("🔗 **Source:** [GitHub Repository](https://github.com/dhruuv-patil/llm-security-gateway)")

    if page == "🚀 Overview":
        st.markdown("<div class='main-header'>Gateway Overview</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        total_reqs = pd.read_sql_query("SELECT COUNT(*) FROM request_logs", conn).iloc[0,0]
        total_tokens = pd.read_sql_query("SELECT SUM(tokens) FROM request_logs", conn).iloc[0,0] or 0
        total_cost = pd.read_sql_query("SELECT SUM(cost) FROM request_logs", conn).iloc[0,0] or 0.0
        threats = pd.read_sql_query("SELECT COUNT(*) FROM request_logs WHERE risk_score > 0", conn).iloc[0,0]
        blocked = pd.read_sql_query("SELECT COUNT(*) FROM harmful_logs", conn).iloc[0,0]
        conn.close()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Traffic", f"{total_reqs:,}")
        col2.metric("Token Consumption", f"{total_tokens:,}")
        col3.metric("Total Expenditure", f"${total_cost:.3f}")
        col4.metric("Security Incidents", int(threats + blocked), delta=int(threats), delta_color="inverse")
        
    elif page == "⚖️ Approvals":
        st.markdown("<div class='main-header'>Pending Approvals</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        df = pd.read_sql_query("SELECT * FROM approval_queue WHERE status='Pending'", conn)
        conn.close()
        
        if df.empty:
            st.success("No pending approvals.")
        else:
            for _, row in df.iterrows():
                with st.container(border=True):
                    st.markdown(f"**Request:** `{row['request_id']}`")
                    st.code(row['prompt'], language="markdown")
                    if st.button("Approve", key=f"app_{row['request_id']}"):
                        requests.post(f"{config.API_BASE_URL}/api/approve/{row['request_id']}")
                        st.rerun()

    elif page == "📈 Analytics":
        st.markdown("<div class='main-header'>Intelligence Analytics</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        df_logs = pd.read_sql_query("SELECT * FROM request_logs", conn)
        conn.close()
        
        if df_logs.empty:
            st.warning("No data.")
        else:
            df_logs['created_at'] = pd.to_datetime(df_logs['created_at'], format='ISO8601', errors='coerce', utc=True)
            df_logs = df_logs.dropna(subset=['created_at'])
            fig = px.area(df_logs.set_index('created_at').resample('H').sum().reset_index(), 
                         x='created_at', y='tokens', title="Token Usage")
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    elif page == "📜 History":
        st.markdown("<div class='main-header'>Interaction Logs</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        df = pd.read_sql_query("SELECT * FROM request_logs ORDER BY created_at DESC", conn)
        conn.close()
        if not df.empty:
            df['response'] = df['response'].apply(crypto.decrypt)
            st.dataframe(df, use_container_width=True)

    elif page == "🛡️ Security":
        st.markdown("<div class='main-header'>Threat Intelligence</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        df_harmful = pd.read_sql_query("SELECT * FROM harmful_logs", conn)
        conn.close()
        st.table(df_harmful)

if __name__ == "__main__":
    run_dashboard()
