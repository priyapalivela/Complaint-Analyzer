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
        display_name = st.text_input(
            "Your Name (optional)",
            key="login_name",
            placeholder="How should we call you?"
        )

        if st.button("Login", type="primary"):
            try:
                conn.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                st.session_state.user_email = email

                if display_name.strip():
                    st.session_state.user_name = display_name.strip().title()
                else:
                    st.session_state.user_name = (
                        email.split("@")[0].replace(".", " ").title()
                    )

                st.success(f"Welcome {st.session_state.user_name}!")
                st.rerun()

            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab2:
        full_name = st.text_input(
            "Full Name",
            key="signup_name",
            placeholder="e.g. Bhanu Priya"
        )
        email = st.text_input("Email", key="signup_email")
        password = st.text_input(
            "Password",
            type="password",
            key="signup_pass"
        )

        if st.button("Create Account", type="primary"):
            if not full_name.strip():
                st.error("Please enter your full name.")
            else:
                try:
                    conn.auth.sign_up(
                        {"email": email, "password": password}
                    )
                    st.success(
                        f"Account created for **{full_name.strip().title()}**! You can now login."
                    )
                except Exception as e:
                    st.error(f"Signup failed: {e}")


if st.session_state.user_email is None:
    login_page()
    st.stop()

# ====================== DISPLAY NAME ======================
user_display_name = (
    st.session_state.get("user_name")
    or (
        st.session_state.user_email.split("@")[0]
        .replace(".", " ")
        .title()
        if st.session_state.user_email
        else "User"
    )
)

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
        st.session_state.complaints = []
        st.rerun()

# ====================== GEMINI ANALYSIS ======================
def analyze_complaint(audio_file, damaged_file, correct_file, order_notes, use_mock=True):
    if use_mock:
        return {
            "damage_analysis": {
                "score": 8,
                "description": "Moderate damage on screen and body."
            },
            "audio_analysis": {
                "transcription": "Hello, I received the phone but the screen is cracked and the camera is not working properly. Very disappointed!",
                "emotions": "Angry",
                "summary": "Customer received a damaged smartphone with cracked screen and malfunctioning camera.",
                "potential_resolution": "Replacement or refund",
            },
            "overall_summary": "High priority complaint — visible product damage.",
        }

    try:
        gemini_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        contents = []

        if damaged_file:
            contents.append(
                genai.protos.Part(
                    inline_data=genai.protos.Blob(
                        mime_type=damaged_file.type,
                        data=damaged_file.getvalue()
                    )
                )
            )
            contents.append(genai.protos.Part(text="Damaged product image"))

        if correct_file:
            contents.append(
                genai.protos.Part(
                    inline_data=genai.protos.Blob(
                        mime_type=correct_file.type,
                        data=correct_file.getvalue()
                    )
                )
            )
            contents.append(genai.protos.Part(text="Correct / reference product image"))

        if audio_file:
            contents.append(
                genai.protos.Part(
                    inline_data=genai.protos.Blob(
                        mime_type=audio_file.type,
                        data=audio_file.getvalue()
                    )
                )
            )
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

        # Strip markdown fences if model wraps response despite instructions
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

# ====================== TABS ======================
tab1, tab2 = st.tabs(["📊 Batch Analysis", "📜 History & Dashboard"])

# ====================== TAB 1 ======================
with tab1:
    st.subheader("Batch Mode — Add Multiple Complaints")

    if st.button("➕ Add New Complaint Set"):
        st.session_state.complaints.append({
            "audio": None,
            "damaged": None,
            "correct": None,
            "order_notes": ""
        })

    if st.session_state.complaints:
        st.write(f"**Current Batch: {len(st.session_state.complaints)} complaints**")
        to_delete = None

        for i, comp in enumerate(st.session_state.complaints, start=1):
            with st.expander(f"Complaint Set {i}", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    comp["audio"] = st.file_uploader(
                        f"Audio Complaint {i}",
                        type=["mp3", "wav", "m4a", "ogg"],
                        key=f"audio_{i}"
                    )

                with col2:
                    comp["order_notes"] = st.text_area(
                        f"Order Notes {i}",
                        key=f"notes_{i}",
                        height=80
                    )

                col3, col4 = st.columns(2)

                with col3:
                    comp["damaged"] = st.file_uploader(
                        f"Damaged Product Image {i}",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"damaged_{i}"
                    )

                with col4:
                    comp["correct"] = st.file_uploader(
                        f"Correct / Reference Image {i}",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"correct_{i}"
                    )

                if st.button(f"❌ Delete Complaint Set {i}", key=f"del_{i}"):
                    to_delete = i - 1

        if to_delete is not None:
            st.session_state.complaints.pop(to_delete)
            st.rerun()

    if st.button("🚀 Process All Complaints", type="primary"):
        save_list = []
        skipped = 0

        for i, comp in enumerate(st.session_state.complaints, start=1):
            if (
                comp["audio"]
                and comp["damaged"]
                and comp["correct"]
                and comp["order_notes"].strip()
            ):
                result = analyze_complaint(
                    comp["audio"],
                    comp["damaged"],
                    comp["correct"],
                    comp["order_notes"],
                    use_mock=use_mock
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
                        st.info("Complaint saved individually.")
                    except Exception as e2:
                        st.error(f"Row insert failed: {e2}")
                        failed_rows.append(row)

        if success_count > 0 and not failed_rows:
            st.success(f"✅ Processed {success_count} complaints!")
            st.session_state.complaints = []
            st.rerun()
        elif failed_rows:
            st.error(f"{len(failed_rows)} complaints could not be saved and remain in the batch for retry.")

# ====================== TAB 2 ======================
with tab2:
    st.subheader("History & Dashboard")

    try:
        response = conn.table("complaints").select("*").eq(
            "user_email", st.session_state.user_email
        ).order("created_at", desc=True).execute()

        df = pd.DataFrame(response.data or [])

        if not df.empty:
            col1, col2, col3 = st.columns(3)

            col1.metric("Total Complaints", len(df))

            col2.metric(
                "Avg Damage Score",
                f"{df['damage_score'].mean():.1f}/10"
                if not df["damage_score"].isnull().all()
                else "N/A",
            )

            col3.metric("User", user_display_name)

        
            if "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

            st.plotly_chart(
                px.bar(
                    df,
                    x="created_at",
                    y="damage_score",
                    title="Damage Score Trend",
                    labels={"created_at": "Date", "damage_score": "Damage Score"}
                ),
                use_container_width=True,
            )

            if "emotions" in df.columns and not df["emotions"].isnull().all():
                emotion_series = (
                    df["emotions"]
                    .dropna()
                    .str.split(",")
                    .str[0]
                    .str.strip()
                    .str.title()
                )
                emotion_counts = emotion_series.value_counts()

                st.plotly_chart(
                    px.pie(
                        values=emotion_counts.values,
                        names=emotion_counts.index,
                        title="Complaints by Primary Emotion",
                    ),
                    use_container_width=True,
                )

            if "resolution" in df.columns and not df["resolution"].isnull().all():
                resolution_counts = df["resolution"].value_counts()

                st.plotly_chart(
                    px.pie(
                        values=resolution_counts.values,
                        names=resolution_counts.index,
                        title="Complaints by Resolution",
                    ),
                    use_container_width=True,
                )

            csv = df.to_csv(index=False).encode()

            st.download_button(
                "⬇️ Download CSV",
                csv,
                "my_complaints.csv",
                "text/csv"
            )

            search = st.text_input("🔎 Search complaints")

            if search:
                mask = df.astype(str).apply(
                    lambda col: col.str.contains(search, case=False, na=False)
                ).any(axis=1)
                df = df[mask]

            st.dataframe(df, use_container_width=True, hide_index=True)

        else:
            st.info("No complaints recorded yet.")

    except Exception as e:
        st.error(f"Database error: {e}")
