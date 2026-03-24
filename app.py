import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Complaint Analyzer", page_icon="🔍", layout="wide")

# ====================== CONNECTION ======================
conn = st.connection("supabase", type=SupabaseConnection)

# ====================== AUTHENTICATION ======================
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None


def login_page():
    st.title("🔐 Complaint Analyzer Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", type="primary"):
            try:
                conn.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user_email = email
                # Optionally pull display name from user metadata if available
                # st.session_state.user_name = resp.user.user_metadata.get("full_name")
                st.success(f"Welcome {email}!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account", type="primary"):
            try:
                conn.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Please check your email to confirm.")
            except Exception as e:
                st.error(f"Signup failed: {e}")


if st.session_state.user_email is None:
    login_page()
    st.stop()

# ====================== DISPLAY NAME ======================
# FIX #1: Define user_display_name BEFORE the sidebar so it's always available.
user_display_name = (
    st.session_state.user_name
    or st.session_state.user_email.split("@")[0].title()
)

# ====================== SIDEBAR ======================
with st.sidebar:
    st.success(f"Logged in as: **{user_display_name}**")
    st.divider()

    # Test mode toggle (set ONCE here, passed into analyze_complaint)
    use_mock = st.toggle("🟢 Test mode (mock data)", value=True)
    if use_mock:
        st.caption("No Gemini quota will be used.")
    else:
        st.caption("⚠️ Real Gemini AI — quota will be consumed.")

    st.divider()
    if st.button("Logout"):
        conn.auth.sign_out()
        # FIX #4: Clear both email AND name on logout to avoid stale state.
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.rerun()


# ====================== GEMINI ANALYSIS ======================
def analyze_complaint(audio_file, damaged_file, correct_file, order_notes, use_mock=True):
    """
    Analyze a complaint using Gemini multimodal AI.
    Pass use_mock=True to skip the real API call and return sample data.
    """
    if use_mock:
        return {
            "damage_analysis": {
                "score": 8,
                "description": "Moderate damage on screen and body. Scratches and dents visible.",
            },
            "audio_analysis": {
                "transcription": (
                    "Hello, I received the phone but the screen is cracked "
                    "and the camera is not working properly. Very disappointed!"
                ),
                "emotions": "Angry, Frustrated",
                "summary": (
                    "Customer received a damaged smartphone with cracked screen "
                    "and malfunctioning camera."
                ),
                "potential_resolution": "Offer replacement or full refund.",
            },
            "overall_summary": "High priority complaint — visible product damage.",
        }

    # Real Gemini call
    try:
        gemini_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        contents = []
        if damaged_file:
            contents.append({"mime_type": damaged_file.type, "data": damaged_file.getvalue()})
            contents.append("Damaged product image")
        if correct_file:
            contents.append({"mime_type": correct_file.type, "data": correct_file.getvalue()})
            contents.append("Correct / reference product image")
        if audio_file:
            contents.append({"mime_type": audio_file.type, "data": audio_file.getvalue()})
            contents.append("Audio complaint — please transcribe and analyse")

        prompt = f"""Order notes: {order_notes}

Analyse the audio and both images provided above.
Return ONLY valid JSON — no markdown, no extra text:
{{
  "damage_analysis": {{"score": <0-10>, "description": "..."}},
  "audio_analysis": {{
    "transcription": "...",
    "emotions": "...",
    "summary": "...",
    "potential_resolution": "..."
  }},
  "overall_summary": "..."
}}"""

        contents.append(prompt)
        response = model.generate_content(contents)
        text = response.text.strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        return {"error": "JSON parse failed", "raw": text}

    except Exception as e:
        st.error(f"Gemini error: {e}")
        return {"error": str(e)}


# ====================== SAVE TO SUPABASE ======================
def save_complaint(data: dict):
    try:
        conn.table("complaints").insert(
            {
                "user_email": st.session_state.user_email,
                "order_notes": data.get("order_notes", ""),
                "damage_score": data.get("damage_score"),
                "damage_description": data.get("damage_description", ""),
                "emotions": data.get("emotions", ""),
                "summary": data.get("summary", ""),
                "resolution": data.get("resolution", ""),
                "overall_summary": data.get("overall_summary", ""),
                "transcription": data.get("transcription", ""),
            }
        ).execute()
        st.success("✅ Saved to database!")
    except Exception as e:
        st.error(f"Save failed: {e}")


# ====================== MAIN UI ======================
st.title(f"🔍 Multimodal Complaint Analyzer — {user_display_name}")

tab1, tab2 = st.tabs(["📊 Batch Analysis", "📜 History & Dashboard"])

# ──────────────────────────────────────────────────────────
# TAB 1 — Batch Analysis
# ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("Batch Mode — Add Multiple Complaints")

    if "complaints" not in st.session_state:
        st.session_state.complaints = []

    # Add new complaint form
    with st.expander("➕ Add New Complaint Set", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            audio = st.file_uploader(
                "Audio Complaint", type=["mp3", "wav", "m4a", "ogg"], key="audio_new"
            )
        with col2:
            order_notes = st.text_area("Order Notes", key="notes_new", height=80)

        col3, col4 = st.columns(2)
        with col3:
            damaged = st.file_uploader(
                "Damaged Product Image",
                type=["jpg", "jpeg", "png", "webp"],
                key="damaged_new",
            )
        with col4:
            correct = st.file_uploader(
                "Correct / Reference Image",
                type=["jpg", "jpeg", "png", "webp"],
                key="correct_new",
            )

        if st.button("Add to Batch"):
            if all([audio, damaged, correct, order_notes.strip()]):
                st.session_state.complaints.append(
                    {
                        "audio": audio,
                        "damaged": damaged,
                        "correct": correct,
                        "order_notes": order_notes,
                    }
                )
                st.success(f"Added! Batch now has {len(st.session_state.complaints)} complaint(s).")
                st.rerun()
            else:
                st.error("All four fields are required before adding to the batch.")

    # Batch summary & process button
    if st.session_state.complaints:
        st.write(f"**Current Batch: {len(st.session_state.complaints)} complaint(s)**")

        preview = [
            {
                "#": i + 1,
                "Order notes": (
                    c["order_notes"][:60] + "…"
                    if len(c["order_notes"]) > 60
                    else c["order_notes"]
                ),
            }
            for i, c in enumerate(st.session_state.complaints)
        ]
        st.dataframe(preview, use_container_width=True, hide_index=True)

        col_proc, col_clear = st.columns([3, 1])
        with col_proc:
            process_btn = st.button("🚀 Process All Complaints", type="primary")
        with col_clear:
            if st.button("🗑️ Clear Batch"):
                st.session_state.complaints = []
                st.rerun()

        if process_btn:
            success_count = 0
            error_count = 0

            with st.status(
                f"Processing {len(st.session_state.complaints)} complaint(s)…",
                expanded=True,
            ) as status:
                for i, comp in enumerate(st.session_state.complaints):
                    st.write(f"Analysing complaint {i + 1} / {len(st.session_state.complaints)}…")

                    # use_mock comes from the sidebar toggle — single source of truth
                    result = analyze_complaint(
                        comp["audio"],
                        comp["damaged"],
                        comp["correct"],
                        comp["order_notes"],
                        use_mock=use_mock,
                    )

                    if "error" in result:
                        st.error(f"Complaint {i + 1} failed: {result['error']}")
                        error_count += 1
                        continue

                    save_data = {
                        "order_notes": comp["order_notes"],
                        "damage_score": result.get("damage_analysis", {}).get("score"),
                        "damage_description": result.get("damage_analysis", {}).get("description", ""),
                        "emotions": result.get("audio_analysis", {}).get("emotions", ""),
                        "summary": result.get("audio_analysis", {}).get("summary", ""),
                        "resolution": result.get("audio_analysis", {}).get("potential_resolution", ""),
                        "overall_summary": result.get("overall_summary", ""),
                        "transcription": result.get("audio_analysis", {}).get("transcription", ""),
                    }
                    save_complaint(save_data)
                    success_count += 1

                status.update(
                    label=f"Done — {success_count} saved, {error_count} failed.",
                    state="complete",
                )

            st.session_state.complaints = []
            st.rerun()

    else:
        st.info("No complaints in the batch yet. Use the form above to add some.")


# ──────────────────────────────────────────────────────────
# TAB 2 — History & Dashboard
# ──────────────────────────────────────────────────────────
with tab2:
    st.subheader("History & Dashboard")

    try:
        response = (
            conn.table("complaints")
            .select("*")
            .eq("user_email", st.session_state.user_email)
            .order("timestamp", desc=True)
            .execute()
        )
        df = pd.DataFrame(response.data or [])

        if not df.empty:
            # KPI metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Complaints", len(df))
            col2.metric(
                "Avg Damage Score",
                f"{df['damage_score'].dropna().mean():.1f} / 10"
                if not df["damage_score"].dropna().empty
                else "N/A",
            )
            col3.metric("Account", st.session_state.user_email)

            st.divider()

            # Charts
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.plotly_chart(
                    px.bar(
                        df,
                        x="timestamp",
                        y="damage_score",
                        title="Damage Score Over Time",
                        labels={"timestamp": "Submitted", "damage_score": "Score"},
                    ),
                    use_container_width=True,
                )
            with chart_col2:
                if "emotions" in df.columns and df["emotions"].notna().any():
                    emotions_series = (
                        df["emotions"]
                        .dropna()
                        .str.split(",")
                        .explode()
                        .str.strip()
                        .value_counts()
                        .reset_index()
                    )
                    emotions_series.columns = ["emotion", "count"]
                    st.plotly_chart(
                        px.pie(
                            emotions_series,
                            names="emotion",
                            values="count",
                            title="Emotion Distribution",
                        ),
                        use_container_width=True,
                    )

            st.divider()

            # CSV download
            csv = df.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download CSV",
                csv,
                "my_complaints.csv",
                "text/csv",
            )

            # Search & table
            search = st.text_input("🔎 Search complaints", placeholder="Type to filter…")
            if search:
                mask = df.apply(lambda row: search.lower() in str(row).lower(), axis=1)
                df = df[mask]

            st.dataframe(df, use_container_width=True, hide_index=True)

        else:
            st.info("No complaints recorded yet. Process a batch in the first tab to get started.")

    except Exception as e:
        st.error(f"Database error: {e}")
