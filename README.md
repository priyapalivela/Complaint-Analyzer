# Complaint Analyzer

A multimodal AI-powered complaint analysis tool built with **Streamlit**, **Gemini 2.5 Flash**, and **Supabase**.

## Features
- User authentication (Email/Password) via Supabase
- Batch upload: Audio complaint + Damaged image + Correct image
- AI Analysis: Damage score, transcription, emotions, summary & resolution suggestions
- Persistent history & dashboard with charts
- Secure secrets management

## Tech Stack
- Streamlit
- Google Gemini (gemini-2.5-flash)
- Supabase (PostgreSQL + Auth)
- Pandas & Plotly

## How to Run Locally

1. Clone the repo
2. Create `.streamlit/secrets.toml` with your Supabase and Gemini keys
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
