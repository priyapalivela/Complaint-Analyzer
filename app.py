import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="AI Complaint Analyzer", page_icon="🔍", layout="wide")

# ====================== CUSTOM CSS ======================
st.markdown("""
<style>
    /* Quick fix for expander hover overlap */
    .streamlit-expanderHeader {
        padding: 12px 16px !important;
    }
    .streamlit-expanderHeader:hover {
        background-color: #2a2a3e !important;
        color: white !important;
    }
    /* Import Google Fonts - but we'll use it selectively */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* ====================== MAIN FONT - NORMAL SANS-SERIF ====================== */
    html, body, [class*="css"], .stApp, 
    .stFileUploader label, .stTextArea label, 
    .stTextInput label, button, .stButton button,
    textarea, input, .stMarkdown, p, span, div {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 
                     'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 
                     sans-serif !important;
        font-weight: 400 !important;           /* Normal weight */
    }

    /* Keep Plus Jakarta Sans only for big headings and section titles */
    h1, h2, h3, .section-header, 
    .stTabs [data-baseweb="tab"], 
    div[data-testid="stMetricValue"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
    }

    .stFileUploader label, 
    .stFileUploader div[data-testid="stMarkdownContainer"] p {
        font-weight: 400 !important;
        font-size: 0.95rem !important;
        color: #cbd5e1 !important;
    }

    textarea {
        font-family: system-ui, -apple-system, sans-serif !important;
        font-weight: 400 !important;
        font-size: 0.98rem !important;
        line-height: 1.5 !important;
    }

    /* Buttons - normal font */
    button, .stButton button {
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.02em;
    }
/
    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.25);
    }
    div[data-testid="metric-container"] label {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: rgba(255,255,255,0.5) !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #a5b4fc !important;
    }

    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 32px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(99,102,241,0.4);
    }

    /* Complaint card */
    .complaint-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 14px;
        border-left: 4px solid #6366f1;
    }
    .complaint-card.high { border-left-color: #ef4444; }
    .complaint-card.medium { border-left-color: #f59e0b; }
    .complaint-card.low { border-left-color: #22c55e; }

    /* Badge */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-right: 6px;
    }
    .badge-angry { background: rgba(239,68,68,0.2); color: #fca5a5; }
    .badge-refund { background: rgba(99,102,241,0.2); color: #a5b4fc; }
    .badge-score { background: rgba(245,158,11,0.2); color: #fcd34d; }

    /* Chart container */
    .chart-container {
        background: linear-gradient(135deg, #1e1e2e 0%, #1a1a2e 100%);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 16px;
        padding: 8px;
        margin-bottom: 20px;
    }

    /* Other small fixes */
    hr { border-color: rgba(99,102,241,0.2) !important; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 100%);
        border-right: 1px solid rgba(99,102,241,0.2);
    }

</style>
""", unsafe_allow_html=True)

# ====================== CONNECTION ======================
conn = st.connection("supabase", type=SupabaseConnection)

# ====================== SESSION STATE ======================
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "complaints" not in st.session_state:
    st.session_state.complaints = []

# ====================== AUTHENTICATION ======================
def login_page():
    st.title("🔐 Complaint Analyzer Login")
    st.markdown("### AI-Powered Voice & Image Complaint Analysis")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        display_name = st.text_input(
            "Your Name (optional)",
            key="login_name",
            placeholder="How should we call you?"
        )

        if st.button("Login", type="primary"):
            try:
                conn.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user_email = email
                st.session_state.user_name = (
                    display_name.strip().title() if display_name.strip()
                    else email.split("@")[0].replace(".", " ").title()
                )
                st.success(f"Welcome {st.session_state.user_name}!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab2:
        full_name = st.text_input("Full Name", key="signup_name", placeholder="e.g. Bhanu Priya")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")

        if st.button("Create Account", type="primary"):
            if not full_name.strip():
                st.error("Please enter your full name.")
            else:
                try:
                    conn.auth.sign_up({"email": email, "password": password})
                    st.success(f"Account created for **{full_name.strip().title()}**! You can now login.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")


if st.session_state.user_email is None:
    login_page()
    st.stop()

# ====================== DISPLAY NAME ======================
user_display_name = (
    st.session_state.get("user_name")
    or (st.session_state.user_email.split("@")[0].replace(".", " ").title()
        if st.session_state.user_email else "User")
)

st.title(f"🔍 AI Complaint Analyzer — {user_display_name}")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.success(f"Logged in as: **{user_display_name}**")
    st.divider()

    use_mock = st.toggle("🟢 Test Mode (Mock Data)", value=False)

    if use_mock:
        st.caption("✅ No Gemini quota will be used — uses sample data")
        st.warning("⚠️ Mock data is generic (phone complaint). Turn off for real AI analysis.")
    else:
        st.caption("⚡ Real Gemini AI — analyzes your actual uploads")

    st.divider()

    if st.button("Logout"):
        conn.auth.sign_out()
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.session_state.complaints = []
        st.rerun()

# ====================== GEMINI ANALYSIS ======================
def analyze_complaint(audio_file, damaged_file, correct_file, order_notes, use_mock=False):
    if use_mock:
        # CLEARLY LABELED mock data — generic placeholder only
        return {
            "damage_analysis": {
                "score": 7,
                "description": "⚠️ MOCK DATA: This is sample output. Turn off Test Mode for real AI analysis."
            },
            "audio_analysis": {
                "transcription": "⚠️ MOCK: Sample transcription. Upload a real audio file and disable Test Mode.",
                "emotions": "Neutral",
                "summary": "⚠️ MOCK: This is placeholder data, not based on your actual uploads.",
                "potential_resolution": "Review required",
            },
            "overall_summary": "⚠️ MOCK DATA — Enable real mode and re-upload for accurate analysis.",
        }

    try:
        gemini_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        contents = []

        if damaged_file:
            contents.append(genai.protos.Part(
                inline_data=genai.protos.Blob(mime_type=damaged_file.type, data=damaged_file.getvalue())
            ))
            contents.append(genai.protos.Part(text="Damaged product image"))

        if correct_file:
            contents.append(genai.protos.Part(
                inline_data=genai.protos.Blob(mime_type=correct_file.type, data=correct_file.getvalue())
            ))
            contents.append(genai.protos.Part(text="Correct / reference product image"))

        if audio_file:
            contents.append(genai.protos.Part(
                inline_data=genai.protos.Blob(mime_type=audio_file.type, data=audio_file.getvalue())
            ))
            contents.append(genai.protos.Part(text="Transcribe this audio complaint"))

        prompt = f"""Order notes: {order_notes}
Analyse the audio and both images.
Return ONLY valid JSON with no markdown fences:

{{
  "damage_analysis": {{"score": <0-10>, "description": "..."}},
  "audio_analysis": {{"transcription": "...", "emotions": "...", "summary": "...", "potential_resolution": "..."}},
  "overall_summary": "..."
}}"""

        contents.append(genai.protos.Part(text=prompt))
        response = model.generate_content(contents)
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end > start:
            return json.loads(text[start:end])

        return {"error": "JSON parse failed"}

    except Exception as e:
        st.error(f"Gemini error: {e}")
        return {"error": str(e)}

# ====================== CHART THEME ======================
CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#cbd5e1"),
    margin=dict(l=20, r=20, t=50, b=20),
)

COLOR_PALETTE = [
    "#6366f1", "#a78bfa", "#38bdf8", "#34d399",
    "#fbbf24", "#f87171", "#fb7185", "#4ade80"
]

def styled_bar_chart(df, x, y, title, color_col=None):
    """Returns a beautifully styled bar chart."""
    color_seq = COLOR_PALETTE
    if color_col:
        fig = px.bar(df, x=x, y=y, color=color_col, title=title, color_discrete_sequence=color_seq)
    else:
        fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=color_seq)

    fig.update_traces(
        marker_line_width=0,
        selector=dict(type="bar")
    )
    fig.update_layout(
        **CHART_THEME,
        title=dict(font=dict(size=16, weight=700), x=0.02),
        xaxis=dict(gridcolor="rgba(99,102,241,0.1)", showline=False, tickfont=dict(size=11)),
        yaxis=dict(gridcolor="rgba(99,102,241,0.1)", showline=False, tickfont=dict(size=11)),
        showlegend=False,
        bargap=0.35,
    )
    # Gradient-like coloring by value for damage scores
    if y == "damage_score":
        colors = []
        for val in df[y]:
            if val >= 8:
                colors.append("#ef4444")
            elif val >= 5:
                colors.append("#f59e0b")
            else:
                colors.append("#22c55e")
        fig.update_traces(marker_color=colors)
    return fig

def styled_pie_chart(values, names, title):
    """Returns a beautifully styled donut chart."""
    fig = go.Figure(go.Pie(
        values=values,
        labels=names,
        hole=0.55,
        textinfo="percent",
        textfont=dict(size=13, family="Plus Jakarta Sans"),
        marker=dict(
            colors=COLOR_PALETTE[:len(names)],
            line=dict(color="rgba(0,0,0,0)", width=0)
        ),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>"
    ))
    fig.update_layout(
        **CHART_THEME,
        title=dict(text=title, font=dict(size=16, weight=700), x=0.02),
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)"
        ),
        annotations=[dict(
            text=f"<b>{sum(values)}</b><br><span style='font-size:10px'>total</span>",
            x=0.5, y=0.5, font_size=20,
            showarrow=False, font=dict(color="#e2e8f0")
        )]
    )
    return fig

def render_complaint_cards(df):
    """Render individual complaint cards with full detail."""
    st.markdown('<div class="section-header">📋 Complaint Details</div>', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        score = row.get("damage_score", 0) or 0
        severity = "high" if score >= 8 else ("medium" if score >= 5 else "low")
        color = "#ef4444" if severity == "high" else ("#f59e0b" if severity == "medium" else "#22c55e")
        
        emotion = str(row.get("emotions", "Unknown")).split(",")[0].strip().title()
        resolution = str(row.get("resolution", "—"))
        created = str(row.get("created_at", ""))[:16].replace("T", " ")

        st.markdown(f"""
        <div class="complaint-card {severity}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                <div>
                    <span style="font-size:0.75rem; color:rgba(255,255,255,0.45); font-weight:600; text-transform:uppercase; letter-spacing:0.06em;">
                        🕐 {created}
                    </span>
                    <div style="font-size:1rem; 
                                font-weight:400;          
                                font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;  
                                color:#e2e8f0; 
                                margin-top:6px; 
                                line-height:1.4;">
                        {str(row.get("order_notes", "—"))[:80]}
                    </div>
                </div>
                <div style="display:flex; gap:8px; align-items:center;">
                    <span class="badge badge-score">Score: {score}/10</span>
                    <span class="badge badge-angry">{emotion}</span>
                </div>
            </div>
            
            <div style="margin-top:14px; font-size:0.875rem; color:#94a3b8; line-height:1.55;">
                <b style="color:#c4b5fd;">📝 Summary:</b> {str(row.get("summary", "—"))[:200]}
            </div>
            <div style="margin-top:8px; font-size:0.875rem; color:#94a3b8; line-height:1.55;">
                <b style="color:#6ee7b7;">✅ Resolution:</b> {resolution[:200]}
            </div>
            <div style="margin-top:8px; font-size:0.875rem; color:#94a3b8; line-height:1.55;">
                <b style="color:#fcd34d;">🔊 Transcription:</b> {str(row.get("transcription", "—"))[:300]}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ====================== TABS ======================
tab1, tab2 = st.tabs(["📊 Batch Analysis", "📜 History & Dashboard"])

# ====================== TAB 1 ======================
with tab1:
    st.subheader("Batch Mode — Add Multiple Complaints")

    if st.button("➕ Add New Complaint Set"):
        st.session_state.complaints.append({
            "audio": None, "damaged": None, "correct": None, "order_notes": ""
        })

    if st.session_state.complaints:
        st.write(f"**Current Batch: {len(st.session_state.complaints)} complaints**")
        to_delete = None

        for i, comp in enumerate(st.session_state.complaints, start=1):
            with st.expander(f"Complaint Set {i}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    comp["audio"] = st.file_uploader(f"Audio Complaint {i}", type=["mp3", "wav", "m4a", "ogg"], key=f"audio_{i}")
                with col2:
                    comp["order_notes"] = st.text_area(f"Order Notes {i}", key=f"notes_{i}", height=80)
                col3, col4 = st.columns(2)
                with col3:
                    comp["damaged"] = st.file_uploader(f"Damaged Product Image {i}", type=["jpg", "jpeg", "png", "webp"], key=f"damaged_{i}")
                with col4:
                    comp["correct"] = st.file_uploader(f"Correct / Reference Image {i}", type=["jpg", "jpeg", "png", "webp"], key=f"correct_{i}")

                if st.button(f"❌ Delete Complaint Set {i}", key=f"del_{i}"):
                    to_delete = i - 1

        if to_delete is not None:
            st.session_state.complaints.pop(to_delete)
            st.rerun()

    if st.button("🚀 Process All Complaints", type="primary"):
        save_list = []
        skipped = 0

        for i, comp in enumerate(st.session_state.complaints, start=1):
            if comp["audio"] and comp["damaged"] and comp["correct"] and comp["order_notes"].strip():
                result = analyze_complaint(
                    comp["audio"], comp["damaged"], comp["correct"],
                    comp["order_notes"], use_mock=use_mock
                )
                if "error" not in result:
                    save_list.append({
                        "user_email": st.session_state.user_email,
                        "order_notes": comp["order_notes"],
                        "damage_score": result.get("damage_analysis", {}).get("score"),
                        "damage_description": result.get("damage_analysis", {}).get("description", ""),
                        "emotions": result.get("audio_analysis", {}).get("emotions", ""),
                        "summary": result.get("audio_analysis", {}).get("summary", ""),
                        "resolution": result.get("audio_analysis", {}).get("potential_resolution", ""),
                        "overall_summary": result.get("overall_summary", ""),
                        "transcription": result.get("audio_analysis", {}).get("transcription", ""),
                    })
            else:
                skipped += 1
                st.warning(f"⚠️ Complaint Set {i} skipped — please attach all files and add order notes.")

        success_count = 0
        failed_rows = []

        if save_list:
            try:
                conn.table("complaints").insert(save_list).execute()
                success_count = len(save_list)
                st.success(f"✅ Bulk saved {success_count} complaints!")
            except Exception as e:
                st.warning(f"Bulk insert failed ({e}), retrying individually...")
                for row in save_list:
                    try:
                        conn.table("complaints").insert(row).execute()
                        success_count += 1
                    except Exception as e2:
                        st.error(f"Row insert failed: {e2}")
                        failed_rows.append(row)

        if success_count > 0 and not failed_rows:
            st.success(f"✅ Processed {success_count} complaints!")
            st.session_state.complaints = []
            st.rerun()
        elif failed_rows:
            st.error(f"{len(failed_rows)} complaints could not be saved.")

# ====================== TAB 2 ======================
with tab2:
    st.subheader("History & Dashboard")

    try:
        response = conn.table("complaints").select("*").eq(
            "user_email", st.session_state.user_email
        ).order("created_at", desc=True).execute()

        df = pd.DataFrame(response.data or [])

        if not df.empty:
            if "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

            # ---- KPI METRICS ----
            col1, col2, col3, col4 = st.columns(4)

            avg_score = df["damage_score"].mean() if not df["damage_score"].isnull().all() else 0
            high_priority = int((df["damage_score"] >= 8).sum()) if "damage_score" in df.columns else 0
            resolved = int(df["resolution"].str.contains("refund|exchange|replacement", case=False, na=False).sum())

            col1.metric("📦 Total Complaints", len(df))
            col2.metric("💥 Avg Damage Score", f"{avg_score:.1f}/10")
            col3.metric("🔴 High Priority", high_priority)
            col4.metric("✅ Resolutions Found", resolved)

            st.divider()

            # ---- ROW 1: Damage Score Trend + Emotion Donut ----
            chart_col1, chart_col2 = st.columns([3, 2])

            with chart_col1:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                trend_df = df.sort_values("created_at")
                fig_bar = styled_bar_chart(
                    trend_df, x="created_at", y="damage_score",
                    title="📈 Damage Score Over Time"
                )
                fig_bar.update_xaxes(tickformat="%b %d\n%H:%M", nticks=8)
                st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with chart_col2:
                if "emotions" in df.columns and not df["emotions"].isnull().all():
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    emotion_series = (
                        df["emotions"].dropna()
                        .str.split(",").str[0]
                        .str.strip().str.title()
                    )
                    emotion_counts = emotion_series.value_counts()
                    fig_emo = styled_pie_chart(
                        emotion_counts.values.tolist(),
                        emotion_counts.index.tolist(),
                        "😤 Complaints by Emotion"
                    )
                    st.plotly_chart(fig_emo, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            # ---- ROW 2: Resolution Donut + Damage Distribution ----
            chart_col3, chart_col4 = st.columns([2, 3])

            with chart_col3:
                if "resolution" in df.columns and not df["resolution"].isnull().all():
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    # Shorten resolution labels for pie chart
                    res_series = df["resolution"].dropna().str[:40].str.strip()
                    res_counts = res_series.value_counts()
                    fig_res = styled_pie_chart(
                        res_counts.values.tolist(),
                        res_counts.index.tolist(),
                        "🛠️ Resolution Breakdown"
                    )
                    st.plotly_chart(fig_res, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            with chart_col4:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                # Damage score distribution as histogram
                fig_hist = go.Figure(go.Histogram(
                    x=df["damage_score"].dropna(),
                    nbinsx=10,
                    marker=dict(
                        color=COLOR_PALETTE[0],
                        line=dict(color="rgba(0,0,0,0)", width=0)
                    ),
                    hovertemplate="Score: %{x}<br>Count: %{y}<extra></extra>"
                ))
                fig_hist.update_layout(
                    **CHART_THEME,
                    title=dict(text="📊 Damage Score Distribution", font=dict(size=16, weight=700), x=0.02),
                    xaxis=dict(title="Damage Score", gridcolor="rgba(99,102,241,0.1)"),
                    yaxis=dict(title="Number of Complaints", gridcolor="rgba(99,102,241,0.1)"),
                    bargap=0.1,
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.divider()

            # ---- COMPLAINT CARDS ----
            render_complaint_cards(df)

            st.divider()

            # ---- SEARCH + TABLE ----
            st.markdown('<div class="section-header">🔎 Search & Export</div>', unsafe_allow_html=True)

            search_col, dl_col = st.columns([3, 1])
            with search_col:
                search = st.text_input("Search complaints by keyword", placeholder="e.g. damaged, refund, angry...")
            with dl_col:
                st.write("")
                st.write("")
                csv = df.to_csv(index=False).encode()
                st.download_button("⬇️ Download CSV", csv, "my_complaints.csv", "text/csv")

            display_df = df.copy()
            if search:
                mask = display_df.astype(str).apply(
                    lambda col: col.str.contains(search, case=False, na=False)
                ).any(axis=1)
                display_df = display_df[mask]

            st.dataframe(display_df, use_container_width=True, hide_index=True)

        else:
            st.info("No complaints recorded yet. Go to **Batch Analysis** to add your first complaint.")

    except Exception as e:
        st.error(f"Database error: {e}")
