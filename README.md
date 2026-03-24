# AI Complaint Analyzer

A modern **multimodal AI-powered** complaint analysis tool that processes customer **voice complaints** along with **damaged** and **correct product images**.

Built with **Streamlit**, **Google Gemini 2.5 Flash**, and **Supabase**.

---

## ✨ Features

- Secure user authentication (Email + Password) using Supabase
- Batch processing of multiple complaints
- AI-powered analysis using Gemini:
  - Damage severity score (0–10)
  - Automatic **audio transcription**
  - Emotion detection
  - Smart summary and resolution suggestions
- Interactive dashboard with charts and metrics
- Persistent data storage in Supabase (PostgreSQL)
- Test Mode to save Gemini quota during development
- Clean and user-friendly interface

---

## 🛠 Tech Stack

| Technology              | Purpose                          |
|------------------------|----------------------------------|
| Streamlit              | Web frontend                     |
| Google Gemini 2.5 Flash| Multimodal AI (Audio + Images)   |
| Supabase               | Database + Authentication        |
| Pandas + Plotly        | Data analysis & Visualization    |

---

## 🚀 How to Run Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/complaint-analyzer.git
   cd complaint-analyzer

Install dependencies:Bashpip install -r requirements.txt
Create .streamlit/secrets.toml file with your credentials (see example below).
Run the app:Bashstreamlit run app.py


🔑 Secrets Configuration
Create a folder .streamlit and add secrets.toml inside it:
toml[connections.supabase]
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

[gemini]
api_key = "AIzaSyYourGeminiAPIKeyHere"
Important: Never commit secrets.toml to GitHub.

📁 Project Structure
textcomplaint-analyzer/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml          # ← Not committed to GitHub

Deployment
This app is designed to be deployed on Streamlit Community Cloud with automatic updates on every git push.

⚠️ Gemini Quota Note

The app includes a Test Mode toggle in the sidebar.
Keep Test Mode ON during development to avoid consuming your Gemini API quota.
Turn it OFF only when you want real AI analysis.


Made With ❤️
Built for fast and intelligent customer complaint resolution.
