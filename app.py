import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Complaint Analyzer", page_icon="🔍", layout="wide")

# ====================== CONNECTION & SECRETS ======================
conn = st.connection("supabase", type=SupabaseConnection)

# ====================== AUTHENTICATION ======================
if "user_email" not in st.session_state:
    st.session_state.user_email = None

def login_page():
    st.title("🔐 Complaint Analyzer Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            try:
                res = conn.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user_email = email
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
                st.success("Account created! Check your email to confirm.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

if st.session_state.user_email is None:
    login_page()
    st.stop()

# ====================== GEMINI ANALYSIS ======================
def analyze_complaint(audio_file, damaged_file, correct_file, order_notes):
    gemini_key = st.secrets["gemini"]["api_key"]
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    contents = []
    if damaged_file:
        contents.append({"mime_type": damaged_file.type, "data": damaged_file.getvalue()})
        contents.append("Damaged product image")
    if correct_file:
        contents.append({"mime_type": correct_file.type, "data": correct_file.getvalue()})
        contents.append("Correct product image")
    if audio_file:
        contents.append({"mime_type": audio_file.type, "data": audio_file.getvalue()})
        contents.append("Transcribe this audio complaint")

    prompt = f"""Order notes: {order_notes}
Analyze audio + two images. Return ONLY valid JSON:
{{
  "damage_analysis": {{"score": <0-10>, "description": "..."}},
  "audio_analysis": {{"transcription": "...", "emotions": "...", "summary": "...", "potential_resolution": "..."}},
  "overall_summary": "..."
}}
JSON only."""

    contents.append(prompt)
    response = model.generate_content(contents)
    text = response.text.strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])
    return {"error": "JSON parse failed"}

# ====================== SAVE TO SUPABASE ======================
def save_complaint(data):
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
            "transcription": data.get("transcription", "")
        }).execute()
        st.success("✅ Saved to cloud database!")
    except Exception as e:
        st.error(f"Save failed: {e}")

# ====================== MAIN UI ======================
st.title(f"Multimodal Complaint Analyzer - {st.session_state.user_email}")

tab1, tab2 = st.tabs(["📊 Batch Analysis", "📜 History & Dashboard"])

with tab1:
    st.subheader("Batch Mode - Add Multiple Complaints")
    if "complaints" not in st.session_state:
        st.session_state.complaints = []

    with st.expander("➕ Add New Complaint Set", expanded=True):
        col1, col2 = st.columns(2)
        with col1: audio = st.file_uploader("Audio Complaint", type=["mp3","wav","m4a","ogg"], key="audio_new")
        with col2: order_notes = st.text_area("Order Notes", key="notes_new", height=80)
        col3, col4 = st.columns(2)
        with col3: damaged = st.file_uploader("Damaged Image", type=["jpg","jpeg","png","webp"], key="damaged_new")
        with col4: correct = st.file_uploader("Correct Image", type=["jpg","jpeg","png","webp"], key="correct_new")

        if st.button("Add to Batch"):
            if all([audio, damaged, correct, order_notes.strip()]):
                st.session_state.complaints.append({
                    "audio": audio, "damaged": damaged, "correct": correct, "order_notes": order_notes
                })
                st.success("Added to batch!")
                st.rerun()
            else:
                st.error("All fields required")

    if st.session_state.complaints:
        st.write(f"**Current Batch: {len(st.session_state.complaints)} complaints**")
        if st.button("🚀 Process All Complaints", type="primary"):
            with st.status("Processing batch with Gemini...", expanded=True):
                for comp in st.session_state.complaints:
                    result = analyze_complaint(comp["audio"], comp["damaged"], comp["correct"], comp["order_notes"])
                    if "error" not in result:
                        save_data = {
                            "order_notes": comp["order_notes"],
                            "damage_score": result.get("damage_analysis", {}).get("score"),
                            "damage_description": result.get("damage_analysis", {}).get("description", ""),
                            "emotions": result.get("audio_analysis", {}).get("emotions", ""),
                            "summary": result.get("audio_analysis", {}).get("summary", ""),
                            "resolution": result.get("audio_analysis", {}).get("potential_resolution", ""),
                            "overall_summary": result.get("overall_summary", ""),
                            "transcription": result.get("audio_analysis", {}).get("transcription", "")
                        }
                        save_complaint(save_data)
            st.success(f"Processed {len(st.session_state.complaints)} complaints!")
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
            col2.metric("Avg Damage Score", f"{df['damage_score'].mean():.1f}/10")
            col3.metric("Logged in as", st.session_state.user_email)

            st.plotly_chart(px.bar(df, x="timestamp", y="damage_score"), use_container_width=True)
            st.plotly_chart(px.pie(df, names="emotions"), use_container_width=True)

            csv = df.to_csv(index=False).encode()
            st.download_button("Download CSV", csv, "my_complaints.csv", "text/csv")

            search = st.text_input("Search")
            if search:
                df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No complaints yet.")
    except Exception as e:
        st.error(f"Database error: {e}")

# Sidebar
with st.sidebar:
    st.success(f"Logged in: {st.session_state.user_email}")
    if st.button("Logout"):
        conn.auth.sign_out()
        st.session_state.user_email = None
        st.rerun()