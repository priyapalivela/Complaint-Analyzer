import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="AI Complaint Analyzer", page_icon="🔍", layout="wide")

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
        # Ask for name at login so returning users can set it
        display_name = st.text_input("Your Name (optional)", key="login_name",
                                     placeholder="How should we call you?")
        if st.button("Login", type="primary"):
            try:
                conn.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user_email = email
                # Use entered name if provided, otherwise fall back to email prefix
                if display_name.strip():
                    st.session_state.user_name = display_name.strip().title()
                else:
                    st.session_state.user_name = email.split("@")[0].replace(".", " ").title()
                st.success(f"Welcome {st.session_state.user_name}!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab2:
        full_name = st.text_input("Full Name", key="signup_name",
                                  placeholder="e.g. Bhanu Priya")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account", type="primary"):
            if not full_name.strip():
                st.error("Please enter your full name.")
            else:
                try:
                    conn.auth.sign_up({"email": email, "password": password})
                    # Store name so user can use it at next login
                    st.success(f"Account created for **{full_name.strip().title()}**! You can now login.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")


if st.session_state.user_email is None:
    login_page()
    st.stop()


# ====================== DISPLAY NAME & MAIN TITLE ======================
user_display_name = st.session_state.get("user_name") or \
                    (st.session_state.user_email.split("@")[0].replace(".", " ").title()
                     if st.session_state.user_email else "User")

st.title(f"🔍 AI Complaint Analyzer — {user_display_name}")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.success(f"Logged in as: **{user_display_name}**")
    st.divider()

    use_mock = st.toggle("🟢 Test Mode (Mock Data)", value=True)
    if use_mock:
        st.caption("✅ No Gemini quota will be used")
    else:
        st.caption("⚠️ Real Gemini AI — quota will be consumed")

    st.divider()
    if st.button("Logout"):
        conn.auth.sign_out()
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.rerun()

# ====================== GEMINI ANALYSIS ======================
def analyze_complaint(audio_file, damaged_file, correct_file, order_notes, use_mock=True):
    if use_mock:
        return {
            "damage_analysis": {"score": 8, "description": "Moderate damage on screen and body."},
            "audio_analysis": {
                "transcription": "Hello, I received the phone but the screen is cracked and the camera is not working properly. Very disappointed!",
                "emotions": "Angry, Frustrated",
                "summary": "Customer received a damaged smartphone with cracked screen and malfunctioning camera.",
                "potential_resolution": "Offer replacement or full refund.",
            },
            "overall_summary": "High priority complaint — visible product damage.",
        }

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
            contents.append("Transcribe this audio complaint")

        prompt = f"""Order notes: {order_notes}
Analyse the audio and both images.
Return ONLY valid JSON:

{{
  "damage_analysis": {{"score": <0-10>, "description": "..."}},
  "audio_analysis": {{"transcription": "...", "emotions": "...", "summary": "...", "potential_resolution": "..."}},
  "overall_summary": "..."
}}"""

        contents.append(prompt)
        response = model.generate_content(contents)
        text = response.text.strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        return {"error": "JSON parse failed"}

    except Exception as e:
        st.error(f"Gemini error: {e}")
        return {"error": str(e)}


# ====================== SAVE TO SUPABASE ======================
def save_complaint(data: dict):
    try:
        conn.table("complaints").insert({
            "user_email": st.session_state.user_email,
            "order_notes": data.get("order_notes", ""),
            "damage_score": data.get("damage_score"),
            "damage_description": data.get("damage_description", ""),
            "emotions": data.get("emotions", ""),
            "summary": data.get("summary", ""),
            "resolution": data.get("resolution", ""),
            "overall_summary": data.get("overall_summary", ""),
            "transcription": data.get("transcription", ""),
        }).execute()
        st.success("✅ Saved to database!")
    except Exception as e:
        st.error(f"Save failed: {e}")


# ====================== TABS ======================
tab1, tab2 = st.tabs(["📊 Batch Analysis", "📜 History & Dashboard"])

with tab1:
    st.subheader("Batch Mode — Add Multiple Complaints")

    with st.expander("➕ Add New Complaint Set", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            audio = st.file_uploader("Audio Complaint", type=["mp3", "wav", "m4a", "ogg"], key="audio_new")
        with col2:
            order_notes = st.text_area("Order Notes", key="notes_new", height=80)

        col3, col4 = st.columns(2)
        with col3:
            damaged = st.file_uploader("Damaged Product Image", type=["jpg","jpeg","png","webp"], key="damaged_new")
        with col4:
            correct = st.file_uploader("Correct / Reference Image", type=["jpg","jpeg","png","webp"], key="correct_new")

        if st.button("Add to Batch"):
            if audio and damaged and correct and order_notes.strip():
                st.session_state.complaints.append({
                    "audio": audio, "damaged": damaged, "correct": correct, "order_notes": order_notes
                })
                st.success(f"Added to batch! Total: {len(st.session_state.complaints)}")
                st.rerun()
            else:
                st.error("All four fields are required.")

    if st.session_state.complaints:
        st.write(f"**Current Batch: {len(st.session_state.complaints)} complaints**")

        if st.button("🚀 Process All Complaints", type="primary"):
            success_count = 0
            with st.status("Processing complaints...", expanded=True):
                for comp in st.session_state.complaints:
                    result = analyze_complaint(
                        comp["audio"], comp["damaged"], comp["correct"], comp["order_notes"], use_mock=use_mock
                    )
                    if "error" not in result:
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

            st.success(f"✅ Processed {success_count} complaints!")
            st.session_state.complaints = []
            st.rerun()

with tab2:
    st.subheader("History & Dashboard")
    try:
        response = conn.table("complaints").select("*").eq("user_email", st.session_state.user_email).order("timestamp", desc=True).execute()
        df = pd.DataFrame(response.data or [])

        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Complaints", len(df))
            col2.metric("Avg Damage Score", f"{df['damage_score'].mean():.1f}/10" if not df['damage_score'].isnull().all() else "N/A")
            col3.metric("User", user_display_name)

            st.plotly_chart(px.bar(df, x="timestamp", y="damage_score", title="Damage Score Trend"), use_container_width=True)

            csv = df.to_csv(index=False).encode()
            st.download_button("⬇️ Download CSV", csv, "my_complaints.csv", "text/csv")

            search = st.text_input("🔎 Search complaints")
            if search:
                df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]

            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No complaints recorded yet.")
    except Exception as e:
        st.error(f"Database error: {e}")
