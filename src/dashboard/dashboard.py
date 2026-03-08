"""
Distributed Job Scheduler — Production Cluster Dashboard.

Premium Streamlit dashboard with dark glassmorphism theme, interactive Plotly
charts, live KPI cards, node heat-map grid, job timeline, and an integrated
job-submission form.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text

from src.utils.config import settings

# ──────────────────────────── page config ────────────────────────────────────
st.set_page_config(
    page_title="Cluster Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────── custom CSS ─────────────────────────────────────
st.markdown(
    """
<style>
/* ── global dark surface ─────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%);
}

/* ── sidebar ─────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(99, 102, 241, 0.15);
}

/* ── metric cards ────────────────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(99, 102, 241, 0.15), inset 0 1px 0 rgba(255,255,255,0.08);
}
div[data-testid="stMetric"] label {
    color: #94a3b8 !important;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-weight: 700;
    font-size: 2rem !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] svg {
    display: none;
}

/* ── glass containers ────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 12px;
    backdrop-filter: blur(10px);
}
div.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
}

/* ── tabs ────────────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {
    color: #94a3b8 !important;
    font-weight: 500;
    font-size: 0.85rem;
    border-radius: 8px 8px 0 0;
    transition: color 0.2s;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #818cf8 !important;
    border-bottom: 2px solid #818cf8;
}

/* ── headings ────────────────────────────────────────────────────────── */
h1, h2, h3 {
    color: #f1f5f9 !important;
    font-weight: 700;
}
h1 { letter-spacing: -0.03em; }

/* ── submit-button accent ────────────────────────────────────────────── */
div.stButton > button[kind="primary"],
div.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.5rem 2rem;
    transition: opacity 0.2s;
}
div.stButton > button:hover {
    opacity: 0.9;
}

/* ── dividers ────────────────────────────────────────────────────────── */
hr {
    border-color: rgba(99, 102, 241, 0.12) !important;
}

/* ── status badge helper ─────────────────────────────────────────────── */
.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
</style>
""",
    unsafe_allow_html=True,
)

# ──────────────────────────── colour palette ─────────────────────────────────
PALETTE = {
    "primary": "#818cf8",    # indigo-400
    "success": "#34d399",    # emerald-400
    "warning": "#fbbf24",    # amber-400
    "danger": "#f87171",     # red-400
    "info": "#38bdf8",       # sky-400
    "purple": "#a78bfa",     # violet-400
    "surface": "#1e293b",    # slate-800
    "bg_dark": "#0f172a",    # slate-900
}

STATUS_COLOURS = {
    "available": PALETTE["success"],
    "busy": PALETTE["warning"],
    "failed": PALETTE["danger"],
    "draining": PALETTE["info"],
    "pending": PALETTE["warning"],
    "running": PALETTE["primary"],
    "completed": PALETTE["success"],
    "cancelled": "#64748b",
    "retry_wait": PALETTE["purple"],
}

def dark_layout(**overrides) -> dict:
    """Return common Plotly layout kwargs for the dark theme.

    Any *overrides* are merged on top so individual charts can customise
    axes, height, legend position, etc. without conflicting with a
    pre-built ``go.Layout`` object.
    """
    base: dict = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#cbd5e1"),
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor="rgba(99,102,241,0.08)", zerolinecolor="rgba(99,102,241,0.08)"),
        yaxis=dict(gridcolor="rgba(99,102,241,0.08)", zerolinecolor="rgba(99,102,241,0.08)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        colorway=[
            PALETTE["primary"],
            PALETTE["success"],
            PALETTE["warning"],
            PALETTE["danger"],
            PALETTE["info"],
            PALETTE["purple"],
        ],
    )
    base.update(overrides)
    return base

# ──────────────────────────── database helpers ───────────────────────────────
engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)


@st.cache_data(ttl=5)
def query_df(sql: str) -> pd.DataFrame:
    """Run *sql* and return a DataFrame (cached 5 s)."""
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch all three primary tables."""
    nodes = query_df(
        "SELECT node_id, cpu_cores, memory_mb, status, current_jobs, last_heartbeat "
        "FROM nodes ORDER BY node_id"
    )
    jobs = query_df(
        """
        SELECT job_id, task_type, status, priority, retry_count,
               node_assigned, submission_time, start_time, completion_time,
               required_cpu, required_memory, execution_time, error_message
        FROM jobs ORDER BY submission_time DESC LIMIT 1000
        """
    )
    metrics = query_df(
        """
        SELECT timestamp, total_nodes, active_nodes, failed_nodes,
               running_jobs, completed_jobs, queue_size, cluster_utilization
        FROM cluster_metrics ORDER BY timestamp DESC LIMIT 500
        """
    )
    return nodes, jobs, metrics


# ──────────────────────────── sidebar ────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Command Center")
    st.caption("Distributed Job Scheduler")
    st.divider()

    auto_refresh = st.toggle("Auto-refresh", value=True)
    refresh_secs = st.slider("Interval (s)", 3, 30, 5, disabled=not auto_refresh)

    st.divider()
    st.markdown("### 🚀 Submit Job")
    with st.form("submit_job", clear_on_submit=True):
        task_type = st.selectbox(
            "Task type",
            ["compute_pi", "matrix_multiplication", "monte_carlo_simulation", "data_processing"],
        )
        col_a, col_b = st.columns(2)
        req_cpu = col_a.number_input("CPU", 1, 32, 2)
        req_mem = col_b.number_input("Memory MB", 128, 65536, 1024, step=256)
        priority = st.slider("Priority", 1, 100, 10)
        exec_time = st.number_input("Exec time (s)", 0.1, 600.0, 5.0, step=0.5)
        submitted = st.form_submit_button("Submit", use_container_width=True)

    if submitted:
        api_url = "http://api:8000"
        try:
            resp = requests.post(
                f"{api_url}/submit_job",
                json={
                    "task_type": task_type,
                    "required_cpu": int(req_cpu),
                    "required_memory": int(req_mem),
                    "priority": int(priority),
                    "execution_time": float(exec_time),
                },
                timeout=5,
            )
            if resp.ok:
                st.success(f"✅ Queued — `{resp.json().get('job_id', '')[:8]}…`")
            else:
                st.error(f"API error: {resp.status_code}")
        except Exception as exc:
            st.error(f"Request failed: {exc}")

    st.divider()
    st.markdown(
        "<div style='text-align:center;color:#475569;font-size:0.7rem'>"
        f"v1.0 · {settings.scheduler_algorithm.upper()} · {settings.cluster_size} nodes"
        "</div>",
        unsafe_allow_html=True,
    )

# ──────────────────────────── load data ──────────────────────────────────────
nodes_df, jobs_df, metrics_df = load_data()

# ──────────────────────────── header ─────────────────────────────────────────
st.markdown(
    """
<div style="display:flex;align-items:center;gap:14px;margin-bottom:4px">
    <span style="font-size:2.2rem">⚡</span>
    <div>
        <h1 style="margin:0;font-size:1.8rem;line-height:1.15">Cluster Command Center</h1>
        <p style="margin:0;color:#64748b;font-size:0.82rem">
            Real-time monitoring · %s algorithm · %d-node cluster
        </p>
    </div>
</div>
"""
    % (settings.scheduler_algorithm.upper(), settings.cluster_size),
    unsafe_allow_html=True,
)

st.markdown("")  # spacer

# ──────────────────────────── KPI row ────────────────────────────────────────
if not metrics_df.empty:
    latest = metrics_df.iloc[0]

    # Compute deltas when possible
    prev = metrics_df.iloc[min(5, len(metrics_df) - 1)]

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Total Nodes", f"{int(latest['total_nodes']):,}")
    c2.metric("Active Nodes", f"{int(latest['active_nodes']):,}",
              delta=int(latest['active_nodes']) - int(prev['active_nodes']))
    c3.metric("Failed Nodes", f"{int(latest['failed_nodes']):,}",
              delta=int(latest['failed_nodes']) - int(prev['failed_nodes']),
              delta_color="inverse")
    c4.metric("Running Jobs", f"{int(latest['running_jobs']):,}",
              delta=int(latest['running_jobs']) - int(prev['running_jobs']))
    c5.metric("Completed", f"{int(latest['completed_jobs']):,}",
              delta=int(latest['completed_jobs']) - int(prev['completed_jobs']))
    c6.metric("Queue Size", f"{int(latest['queue_size']):,}",
              delta=int(latest['queue_size']) - int(prev['queue_size']),
              delta_color="inverse")
    c7.metric("Utilization", f"{latest['cluster_utilization']:.1%}")
else:
    st.info("Waiting for cluster metrics data…")

st.divider()

# ──────────────────────────── tabs ───────────────────────────────────────────
tab_overview, tab_nodes, tab_jobs, tab_timeline = st.tabs(
    ["📊 Overview", "🖥️ Nodes", "📋 Jobs", "⏱️ Timeline"]
)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    col_left, col_right = st.columns([3, 2], gap="large")

    # ── cluster utilization area chart ──────────────────────────────────
    with col_left:
        st.markdown("#### Cluster Utilization Timeline")
        if not metrics_df.empty:
            mdf = metrics_df.sort_values("timestamp").copy()
            fig_util = go.Figure()
            fig_util.add_trace(go.Scatter(
                x=mdf["timestamp"], y=mdf["cluster_utilization"] * 100,
                mode="lines", name="Utilization %",
                line=dict(color=PALETTE["primary"], width=2.5),
                fill="tozeroy",
                fillcolor="rgba(129,140,248,0.12)",
            ))
            fig_util.add_trace(go.Scatter(
                x=mdf["timestamp"], y=mdf["running_jobs"],
                mode="lines", name="Running Jobs",
                line=dict(color=PALETTE["success"], width=2, dash="dot"),
                yaxis="y2",
            ))
            # apply template via the `template` argument to avoid duplicate axis kwargs
            fig_util.update_layout(
                **dark_layout(
                    height=340,
                    yaxis=dict(
                        title="Utilization %", range=[0, 105],
                        gridcolor="rgba(99,102,241,0.08)",
                    ),
                    yaxis2=dict(
                        title="Running Jobs", overlaying="y", side="right",
                        gridcolor="rgba(99,102,241,0.06)",
                    ),
                    legend=dict(orientation="h", y=-0.18),
                    hovermode="x unified",
                ),
            )
            st.plotly_chart(fig_util, use_container_width=True, config={"displayModeBar": False})

    # ── queue depth area chart ──────────────────────────────────────────
    with col_right:
        st.markdown("#### Queue & Throughput")
        if not metrics_df.empty:
            mdf2 = metrics_df.sort_values("timestamp").copy()
            fig_q = go.Figure()
            fig_q.add_trace(go.Scatter(
                x=mdf2["timestamp"], y=mdf2["queue_size"],
                mode="lines", name="Queue Depth",
                line=dict(color=PALETTE["warning"], width=2),
                fill="tozeroy",
                fillcolor="rgba(251,191,36,0.1)",
            ))
            fig_q.add_trace(go.Scatter(
                x=mdf2["timestamp"], y=mdf2["completed_jobs"],
                mode="lines", name="Completed (cumul.)",
                line=dict(color=PALETTE["success"], width=2),
            ))
            fig_q.update_layout(
                **dark_layout(),
                height=340,
                legend=dict(orientation="h", y=-0.18),
                hovermode="x unified",
            )
            st.plotly_chart(fig_q, use_container_width=True, config={"displayModeBar": False})

    st.markdown("")

    # ── second row: node health + job status ────────────────────────────
    col_a, col_b, col_c = st.columns(3, gap="large")

    with col_a:
        st.markdown("#### Node Health")
        if not nodes_df.empty:
            status_counts = nodes_df["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            fig_nh = go.Figure(go.Pie(
                labels=status_counts["status"],
                values=status_counts["count"],
                hole=0.55,
                marker=dict(
                    colors=[STATUS_COLOURS.get(s, "#64748b") for s in status_counts["status"]],
                    line=dict(color=PALETTE["bg_dark"], width=2),
                ),
                textinfo="label+percent",
                textfont=dict(size=12),
            ))
            fig_nh.update_layout(
                **dark_layout(),
                height=290,
                showlegend=False,
                annotations=[dict(
                    text=f"<b>{len(nodes_df)}</b><br><span style='font-size:10px;color:#94a3b8'>nodes</span>",
                    x=0.5, y=0.5, font_size=22, showarrow=False, font_color="#f1f5f9",
                )],
            )
            st.plotly_chart(fig_nh, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No nodes registered yet.")

    with col_b:
        st.markdown("#### Job Status")
        if not jobs_df.empty:
            js_counts = jobs_df["status"].value_counts().reset_index()
            js_counts.columns = ["status", "count"]
            fig_js = go.Figure(go.Pie(
                labels=js_counts["status"],
                values=js_counts["count"],
                hole=0.55,
                marker=dict(
                    colors=[STATUS_COLOURS.get(s, "#64748b") for s in js_counts["status"]],
                    line=dict(color=PALETTE["bg_dark"], width=2),
                ),
                textinfo="label+percent",
                textfont=dict(size=12),
            ))
            fig_js.update_layout(
                **dark_layout(),
                height=290,
                showlegend=False,
                annotations=[dict(
                    text=f"<b>{len(jobs_df)}</b><br><span style='font-size:10px;color:#94a3b8'>jobs</span>",
                    x=0.5, y=0.5, font_size=22, showarrow=False, font_color="#f1f5f9",
                )],
            )
            st.plotly_chart(fig_js, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No jobs submitted yet.")

    with col_c:
        st.markdown("#### Task Type Mix")
        if not jobs_df.empty:
            tt_counts = jobs_df["task_type"].value_counts().reset_index()
            tt_counts.columns = ["task_type", "count"]
            fig_tt = go.Figure(go.Bar(
                x=tt_counts["count"],
                y=tt_counts["task_type"],
                orientation="h",
                marker=dict(
                    color=tt_counts["count"],
                    colorscale=[[0, PALETTE["primary"]], [1, PALETTE["purple"]]],
                    cornerradius=6,
                ),
                text=tt_counts["count"],
                textposition="auto",
                textfont=dict(color="#f1f5f9", size=12, family="Inter"),
            ))
            fig_tt.update_layout(
                **dark_layout(),
                height=290,
                yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
                xaxis=dict(title="Job Count", gridcolor="rgba(99,102,241,0.08)"),
                showlegend=False,
            )
            st.plotly_chart(fig_tt, use_container_width=True, config={"displayModeBar": False})

    # ── retry distribution ──────────────────────────────────────────────
    if not jobs_df.empty and jobs_df["retry_count"].max() > 0:
        st.markdown("#### Retry Distribution")
        retry_data = jobs_df.groupby("retry_count").size().reset_index(name="count")
        fig_retry = go.Figure(go.Bar(
            x=retry_data["retry_count"],
            y=retry_data["count"],
            marker=dict(
                color=[PALETTE["success"] if r == 0 else PALETTE["warning"] if r < 3 else PALETTE["danger"]
                       for r in retry_data["retry_count"]],
                cornerradius=8,
            ),
            text=retry_data["count"],
            textposition="outside",
            textfont=dict(color="#cbd5e1"),
        ))
        fig_retry.update_layout(
            **dark_layout(),
            height=240,
            xaxis=dict(title="Retry Count", dtick=1),
            yaxis=dict(title="Jobs"),
        )
        st.plotly_chart(fig_retry, use_container_width=True, config={"displayModeBar": False})


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — NODES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_nodes:
    if not nodes_df.empty:
        st.markdown("#### Node Grid — Hover for Details")

        # Build a heat-map grid (10 columns)
        _cols = 10
        _rows = math.ceil(len(nodes_df) / _cols)
        status_map = {"available": 0, "busy": 1, "draining": 2, "failed": 3}
        colour_scale = [
            [0, PALETTE["success"]],
            [0.33, PALETTE["warning"]],
            [0.66, PALETTE["info"]],
            [1, PALETTE["danger"]],
        ]

        z_vals: list[list[float | None]] = []
        hover: list[list[str]] = []
        for r in range(_rows):
            z_row: list[float | None] = []
            h_row: list[str] = []
            for c in range(_cols):
                idx = r * _cols + c
                if idx < len(nodes_df):
                    row = nodes_df.iloc[idx]
                    z_row.append(status_map.get(row["status"], 0))
                    h_row.append(
                        f"<b>{row['node_id']}</b><br>"
                        f"Status: {row['status']}<br>"
                        f"CPU: {row['cpu_cores']} cores<br>"
                        f"Mem: {row['memory_mb']} MB<br>"
                        f"Jobs: {row['current_jobs']}"
                    )
                else:
                    z_row.append(None)
                    h_row.append("")
            z_vals.append(z_row)
            hover.append(h_row)

        fig_grid = go.Figure(go.Heatmap(
            z=z_vals,
            hovertext=hover,
            hoverinfo="text",
            colorscale=colour_scale,
            showscale=False,
            xgap=3,
            ygap=3,
            zmin=0,
            zmax=3,
        ))
        fig_grid.update_layout(
            **dark_layout(),
            height=max(180, _rows * 40),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(showticklabels=False, showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig_grid, use_container_width=True, config={"displayModeBar": False})

        # Legend helper
        st.markdown(
            """<div style="display:flex;gap:20px;justify-content:center;margin-top:-10px">
            <span style="color:{0}">● Available</span>
            <span style="color:{1}">● Busy</span>
            <span style="color:{2}">● Draining</span>
            <span style="color:{3}">● Failed</span>
            </div>""".format(PALETTE["success"], PALETTE["warning"], PALETTE["info"], PALETTE["danger"]),
            unsafe_allow_html=True,
        )

        st.markdown("")

        # ── per-node load bar chart (top 30 busiest) ────────────────────
        st.markdown("#### Top Nodes by Running Jobs")
        busy = nodes_df.nlargest(30, "current_jobs")
        if busy["current_jobs"].max() > 0:
            fig_load = go.Figure(go.Bar(
                x=busy["node_id"],
                y=busy["current_jobs"],
                marker=dict(
                    color=busy["current_jobs"],
                    colorscale=[[0, PALETTE["success"]], [0.5, PALETTE["warning"]], [1, PALETTE["danger"]]],
                    cornerradius=4,
                ),
                text=busy["current_jobs"],
                textposition="outside",
                textfont=dict(color="#cbd5e1", size=10),
            ))
            fig_load.update_layout(
                **dark_layout(),
                height=280,
                xaxis=dict(tickangle=-60, tickfont=dict(size=9)),
                yaxis=dict(title="Running Jobs"),
            )
            st.plotly_chart(fig_load, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("All nodes are currently idle.")

        # ── detailed node table ─────────────────────────────────────────
        with st.expander("🔍 Full Node Table", expanded=False):
            st.dataframe(
                nodes_df.style.map(
                    lambda v: f"color: {STATUS_COLOURS.get(v, '#cbd5e1')}",
                    subset=["status"],
                ),
                use_container_width=True,
                height=400,
            )
    else:
        st.info("No nodes registered yet. Start the scheduler or cluster simulator.")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — JOBS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_jobs:
    if not jobs_df.empty:
        # ── filters ─────────────────────────────────────────────────────
        st.markdown("#### Job Explorer")
        f1, f2, f3 = st.columns(3)
        status_filter = f1.multiselect(
            "Status", options=sorted(jobs_df["status"].unique()),
            default=sorted(jobs_df["status"].unique()),
        )
        task_filter = f2.multiselect(
            "Task Type", options=sorted(jobs_df["task_type"].unique()),
            default=sorted(jobs_df["task_type"].unique()),
        )
        priority_range = f3.slider("Priority", 1, 100, (1, 100))

        filtered = jobs_df[
            (jobs_df["status"].isin(status_filter))
            & (jobs_df["task_type"].isin(task_filter))
            & (jobs_df["priority"] >= priority_range[0])
            & (jobs_df["priority"] <= priority_range[1])
        ]

        st.caption(f"Showing **{len(filtered):,}** of **{len(jobs_df):,}** jobs")

        # ── priority distribution ───────────────────────────────────────
        col_p, col_s = st.columns(2, gap="large")
        with col_p:
            st.markdown("##### Priority Distribution")
            fig_pd = go.Figure(go.Histogram(
                x=filtered["priority"],
                nbinsx=20,
                marker=dict(
                    color=PALETTE["primary"],
                    line=dict(color=PALETTE["bg_dark"], width=1),
                    cornerradius=4,
                ),
            ))
            fig_pd.update_layout(
                **dark_layout(),
                height=260,
                xaxis=dict(title="Priority"),
                yaxis=dict(title="Count"),
            )
            st.plotly_chart(fig_pd, use_container_width=True, config={"displayModeBar": False})

        with col_s:
            st.markdown("##### Status Breakdown")
            status_g = filtered["status"].value_counts().reset_index()
            status_g.columns = ["status", "count"]
            fig_sb = go.Figure(go.Bar(
                x=status_g["status"],
                y=status_g["count"],
                marker=dict(
                    color=[STATUS_COLOURS.get(s, "#64748b") for s in status_g["status"]],
                    cornerradius=6,
                ),
                text=status_g["count"],
                textposition="outside",
                textfont=dict(color="#cbd5e1"),
            ))
            fig_sb.update_layout(
                **dark_layout(),
                height=260,
                yaxis=dict(title="Count"),
            )
            st.plotly_chart(fig_sb, use_container_width=True, config={"displayModeBar": False})

        # ── resource scatter (CPU vs Memory) ────────────────────────────
        if "required_cpu" in filtered.columns and "required_memory" in filtered.columns:
            st.markdown("##### Resource Allocation — CPU vs Memory")
            fig_res = px.scatter(
                filtered,
                x="required_cpu",
                y="required_memory",
                color="status",
                size="priority",
                hover_data=["job_id", "task_type", "retry_count"],
                color_discrete_map=STATUS_COLOURS,
                size_max=18,
                opacity=0.75,
            )
            fig_res.update_layout(
                **dark_layout(),
                height=350,
                xaxis=dict(title="Required CPU Cores"),
                yaxis=dict(title="Required Memory (MB)"),
            )
            st.plotly_chart(fig_res, use_container_width=True, config={"displayModeBar": False})

        # ── detailed table ──────────────────────────────────────────────
        with st.expander("🔍 Full Job Table", expanded=False):
            display_cols = [
                "job_id", "task_type", "status", "priority", "required_cpu",
                "required_memory", "retry_count", "node_assigned",
                "submission_time", "completion_time",
            ]
            available_cols = [c for c in display_cols if c in filtered.columns]
            st.dataframe(
                filtered[available_cols].style.map(
                    lambda v: f"color: {STATUS_COLOURS.get(v, '#cbd5e1')}",
                    subset=["status"],
                ),
                use_container_width=True,
                height=400,
            )
    else:
        st.info("No jobs have been submitted yet.")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_timeline:
    if not jobs_df.empty:
        completed = jobs_df.dropna(subset=["start_time", "completion_time"]).head(80)
        if not completed.empty:
            st.markdown("#### Job Execution Timeline (Gantt)")
            completed = completed.copy()
            completed["start_time"] = pd.to_datetime(completed["start_time"])
            completed["completion_time"] = pd.to_datetime(completed["completion_time"])
            completed["duration_s"] = (
                completed["completion_time"] - completed["start_time"]
            ).dt.total_seconds()

            fig_gantt = px.timeline(
                completed,
                x_start="start_time",
                x_end="completion_time",
                y="node_assigned",
                color="status",
                color_discrete_map=STATUS_COLOURS,
                hover_data=["job_id", "task_type", "duration_s", "retry_count"],
                opacity=0.85,
            )
            fig_gantt.update_layout(
                **dark_layout(),
                height=max(350, len(completed["node_assigned"].unique()) * 28),
                yaxis=dict(title="Node", categoryorder="category ascending", tickfont=dict(size=9)),
                xaxis=dict(title="Time"),
            )
            fig_gantt.update_traces(marker_line_width=0)
            st.plotly_chart(fig_gantt, use_container_width=True, config={"displayModeBar": False})

            # ── execution-time histogram ────────────────────────────────
            st.markdown("#### Job Duration Distribution (seconds)")
            fig_dur = go.Figure(go.Histogram(
                x=completed["duration_s"],
                nbinsx=25,
                marker=dict(
                    color=PALETTE["info"],
                    line=dict(color=PALETTE["bg_dark"], width=1),
                    cornerradius=4,
                ),
            ))
            fig_dur.update_layout(
                **dark_layout(),
                height=240,
                xaxis=dict(title="Duration (s)"),
                yaxis=dict(title="Count"),
            )
            st.plotly_chart(fig_dur, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No completed jobs with timing data yet.")

        # ── scheduling latency ──────────────────────────────────────────
        latency_df = jobs_df.dropna(subset=["submission_time", "start_time"]).head(200).copy()
        if not latency_df.empty:
            latency_df["submission_time"] = pd.to_datetime(latency_df["submission_time"])
            latency_df["start_time"] = pd.to_datetime(latency_df["start_time"])
            latency_df["latency_s"] = (
                latency_df["start_time"] - latency_df["submission_time"]
            ).dt.total_seconds()

            st.markdown("#### Scheduling Latency Over Time")
            latency_df_sorted = latency_df.sort_values("submission_time")
            fig_lat = go.Figure(go.Scatter(
                x=latency_df_sorted["submission_time"],
                y=latency_df_sorted["latency_s"],
                mode="lines+markers",
                marker=dict(size=4, color=PALETTE["purple"]),
                line=dict(color=PALETTE["purple"], width=1.5),
                fill="tozeroy",
                fillcolor="rgba(167,139,250,0.08)",
            ))
            fig_lat.update_layout(
                **dark_layout(),
                height=260,
                xaxis=dict(title="Submission Time"),
                yaxis=dict(title="Latency (s)"),
            )
            st.plotly_chart(fig_lat, use_container_width=True, config={"displayModeBar": False})


# ──────────────────────────── footer ────────────────────────────────────────
st.divider()
footer_cols = st.columns([3, 1])
with footer_cols[0]:
    st.markdown(
        "<span style='color:#475569;font-size:0.75rem'>"
        "Distributed Job Scheduler Dashboard · "
        f"Last refresh: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        "</span>",
        unsafe_allow_html=True,
    )
with footer_cols[1]:
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

# ──────────────────────────── auto-refresh ──────────────────────────────────
if auto_refresh:
    time.sleep(refresh_secs)
    st.rerun()
