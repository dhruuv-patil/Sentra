import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px
from core.config import config
from core.crypto import crypto
from core.cache import cache
from data.database import Database
from data.repository import Repository
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
        st.metric("Cached Responses", cache.count())
        if st.button("Clear Response Cache"):
            cache.clear()
            st.toast("Cache cleared successfully!")
            st.rerun()

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
        pending_count = pd.read_sql_query("SELECT COUNT(*) FROM approval_queue WHERE status='Pending'", conn).iloc[0,0]
        conn.close()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Traffic", f"{total_reqs:,}")
        col2.metric("Token Consumption", f"{total_tokens:,}")
        col3.metric("Total Expenditure", f"${total_cost:.4f}")
        col4.metric("Security Incidents", int(threats + blocked), delta=int(threats), delta_color="inverse")
        col5.metric("Pending Approvals", int(pending_count))

        st.markdown("### Quick Gateway Architecture")
        st.info("Input Guardrails (Prompt Shielding + PII Masking) ➔ Cache Check ➔ Provider Dispatcher (Groq / Ollama) ➔ Output Guardrails ➔ AES Encrypted Audit Trail")

    elif page == "⚖️ Approvals":
        st.markdown("<div class='main-header'>Human-in-the-Loop Governance</div>", unsafe_allow_html=True)
        tab_pending, tab_history = st.tabs(["⏳ Pending Authorizations", "📜 Review Decision Log"])

        with tab_pending:
            df_pending = Repository.get_pending_approvals()
            if df_pending.empty:
                st.success("No requests currently pending approval. All incoming traffic conforms to security baseline.")
            else:
                for _, row in df_pending.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**Request ID:** `{row['request_id']}` | **Model:** `{row['model']}` | **Submitted:** `{row['created_at']}`")
                        st.code(row['prompt'], language="markdown")
                        
                        col_btn1, col_btn2, _ = st.columns([1, 1, 4])
                        with col_btn1:
                            if st.button("✅ Approve & Run", key=f"app_{row['request_id']}", use_container_width=True):
                                res = requests.post(f"{config.API_BASE_URL}/api/approve/{row['request_id']}")
                                if res.status_code == 200:
                                    st.toast("Request approved and executed!")
                                else:
                                    st.error(f"Approval error: {res.text}")
                                time.sleep(0.5)
                                st.rerun()

                        with col_btn2:
                            if st.button("❌ Deny Request", key=f"deny_{row['request_id']}", use_container_width=True):
                                res = requests.post(f"{config.API_BASE_URL}/api/deny/{row['request_id']}")
                                if res.status_code == 200:
                                    st.toast("Request denied.")
                                else:
                                    st.error(f"Denial error: {res.text}")
                                time.sleep(0.5)
                                st.rerun()

        with tab_history:
            df_all = Repository.get_all_approvals()
            if df_all.empty:
                st.info("No approval actions recorded yet.")
            else:
                st.dataframe(df_all, use_container_width=True)

    elif page == "📈 Analytics":
        st.markdown("<div class='main-header'>Intelligence Analytics</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        df_logs = pd.read_sql_query("SELECT * FROM request_logs", conn)
        conn.close()
        
        if df_logs.empty:
            st.warning("No analytics data available yet. Route prompts through port 8000 to generate telemetry.")
        else:
            df_logs['created_at'] = pd.to_datetime(df_logs['created_at'], format='ISO8601', errors='coerce', utc=True)
            df_logs = df_logs.dropna(subset=['created_at'])

            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                fig_tokens = px.area(
                    df_logs.set_index('created_at').resample('min').sum().reset_index(),
                    x='created_at', y='tokens', title="Token Consumption Over Time",
                    color_discrete_sequence=["#00f2fe"]
                )
                fig_tokens.update_layout(template="plotly_dark")
                st.plotly_chart(fig_tokens, use_container_width=True)

            with col_chart2:
                fig_risk = px.histogram(
                    df_logs, x='risk_score', nbins=20, title="Risk Score Distribution",
                    color_discrete_sequence=["#ff5252"]
                )
                fig_risk.update_layout(template="plotly_dark")
                st.plotly_chart(fig_risk, use_container_width=True)

    elif page == "📜 History":
        st.markdown("<div class='main-header'>Audit Log Explorer (Decrypted)</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        df = pd.read_sql_query("SELECT * FROM request_logs ORDER BY created_at DESC LIMIT 200", conn)
        conn.close()
        if not df.empty and 'response' in df.columns:
            df['response'] = df['response'].apply(lambda x: crypto.decrypt(x) if isinstance(x, str) and x.startswith('gAAAAA') else x)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Audit log is currently empty.")

    elif page == "🛡️ Security":
        st.markdown("<div class='main-header'>Threat Intelligence & Violations</div>", unsafe_allow_html=True)
        conn = Database.get_connection()
        df_harmful = pd.read_sql_query("SELECT * FROM harmful_logs ORDER BY created_at DESC", conn)
        conn.close()
        if not df_harmful.empty:
            st.table(df_harmful)
        else:
            st.success("Zero security policy violations or harmful outputs logged.")

if __name__ == "__main__":
    run_dashboard()
