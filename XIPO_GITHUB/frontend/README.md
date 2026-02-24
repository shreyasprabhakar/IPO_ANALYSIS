# XIPO Streamlit UI - Setup Guide

## Files Created

- `frontend/app.py` - Main Streamlit application
- `frontend/requirements.txt` - Python dependencies

## How to Run

### 1. Start the Backend (Terminal 1)

```bash
cd backend
uvicorn app.main:app --reload
```

The backend will run on `http://127.0.0.1:8000`

### 2. Install Frontend Dependencies (First Time Only)

```bash
cd frontend
pip install -r requirements.txt
```

### 3. Start the Streamlit UI (Terminal 2)

```bash
cd frontend
streamlit run app.py
```

The UI will open automatically in your browser at `http://localhost:8501`

## Using the UI

1. **Analyze an IPO**:
   - Enter a company name (e.g., "Awfis", "Meesho", "Lenskart")
   - Click "Analyze IPO"
   - View the health score and detailed report

2. **Ask Questions**:
   - After analysis, scroll to the chatbot section
   - Type your question
   - Click "Ask" to get AI-powered answers
   - Chat history is maintained during the session

## Features

- **Health Score Display**: Visual card showing score, category, and explanation
- **IPO Report**: Structured sections including:
  - Company Overview
  - Business Model
  - Key Strengths
  - Key Risks
  - Financial Highlights
  - Use of Proceeds
  - Management
  - Investment Recommendation

- **Chatbot Q&A**: Ask follow-up questions about the IPO
- **Error Handling**: Shows suggestions when company not found
- **Session State**: Maintains analysis and chat history

## Troubleshooting

**Backend not responding:**
- Ensure backend is running on port 8000
- Check terminal for errors

**Company not found:**
- Try the exact company name from SEBI filings
- Check the suggestions list for similar companies

**Streamlit errors:**
- Ensure all dependencies are installed
- Try `pip install --upgrade streamlit requests`
