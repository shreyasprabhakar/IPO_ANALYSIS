"""
XIPO - IPO RHP Analyzer
Streamlit frontend for analyzing IPO prospectuses
"""

import streamlit as st
import requests
from typing import Optional, Dict, Any

# Backend API configuration
BACKEND_URL = "http://127.0.0.1:8000"

# Page configuration
st.set_page_config(
    page_title="XIPO - IPO RHP Analyzer",
    page_icon="📊",
    layout="wide",
)

# Initialize session state
if "analyzed_company" not in st.session_state:
    st.session_state.analyzed_company = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "debug_response" not in st.session_state:
    st.session_state.debug_response = None
if "is_analyzing" not in st.session_state:
    st.session_state.is_analyzing = False
if "developer_mode" not in st.session_state:
    st.session_state.developer_mode = False


def analyze_company(company_name: str) -> Optional[Dict[str, Any]]:
    """Call backend /api/api/analyze endpoint."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/api/analyze",
            json={
                "company_name": company_name.strip(),
                "top_k": 6,
                "debug": False,
            },
            timeout=600,
        )

        # Store debug info
        debug_info = {
            "status_code": response.status_code,
            "url": response.url,
            "response_text": response.text[:1000],  # First 1000 chars
        }

        try:
            response_json = response.json()
            debug_info["response_json"] = response_json
        except:
            response_json = None

        if response.status_code == 200:
            return {
                "status": "success",
                "data": response_json,
                "debug": debug_info,
            }
        elif response.status_code == 404:
            return {
                "status": "not_found",
                "data": response_json if response_json else {},
                "debug": debug_info,
            }
        else:
            return {
                "status": "error",
                "status_code": response.status_code,
                "message": response.text,
                "data": response_json if response_json else {},
                "debug": debug_info,
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "debug": {"error": str(e)},
        }


def ask_question(company_name: str, question: str) -> Optional[Dict[str, Any]]:
    """Call backend /api/api/rag/ask endpoint."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/api/rag/ask",
            json={
                "company_name": company_name,
                "question": question,
                "top_k": 6,
                "debug": False,
            },
            timeout=60,
        )

        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Connection error: {str(e)}"}


def display_health_score(health_score_data: Dict[str, Any]):
    """Display health score in a highlighted card."""
    score = health_score_data.get("score", 0)
    category = health_score_data.get("category", "Unknown")
    explanation = health_score_data.get("explanation", "")

    # Color coding based on category
    color_map = {
        "Excellent": "🟢",
        "Good": "🟡",
        "Fair": "🟠",
        "Poor": "🔴",
    }
    emoji = color_map.get(category, "⚪")

    st.markdown("### 📊 Financial Health Score")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric(
            label="Score",
            value=f"{score}/100",
            delta=category,
        )

    with col2:
        st.markdown(f"{emoji} **{category}**")
        st.caption(explanation)



def clean_report_text(text: str) -> str:
    """
    Clean up report text by checking for error keywords.
    If an error is found, return a user-friendly message.
    """
    if not text:
        return ""
        
    error_keywords = [
        "Error retrieving information",
        "Failed to call Ollama",
        "Read timed out",
    ]
    
    for keyword in error_keywords:
        if keyword in text:
            return "This section could not be generated due to a temporary LLM timeout. Please try again."
            
    return text


def display_report(report_data: Dict[str, Any]):
    """Display the default IPO analysis report."""
    st.markdown("### 📄 IPO Analysis Report")

    # Company Overview
    if "company_overview" in report_data:
        st.subheader("Company Overview")
        st.write(clean_report_text(report_data["company_overview"]))

    # Business Model
    if "business_model" in report_data:
        st.subheader("Business Model")
        st.write(clean_report_text(report_data["business_model"]))

    # Strengths
    if "strengths" in report_data:
        st.subheader("✅ Key Strengths")
        strengths = report_data["strengths"]
        if isinstance(strengths, list):
            for strength in strengths:
                st.markdown(f"- {clean_report_text(strength)}")
        else:
            st.write(clean_report_text(strengths))

    # Risks
    if "risks" in report_data:
        st.subheader("⚠️ Key Risks")
        risks = report_data["risks"]
        if isinstance(risks, list):
            for risk in risks:
                st.markdown(f"- {clean_report_text(risk)}")
        else:
            st.write(clean_report_text(risks))

    # Financial Highlights
    if "financial_highlights" in report_data:
        st.subheader("💰 Financial Highlights")
        st.write(clean_report_text(report_data["financial_highlights"]))

    # Use of Proceeds
    if "use_of_proceeds" in report_data:
        st.subheader("💵 Use of Proceeds")
        st.write(clean_report_text(report_data["use_of_proceeds"]))

    # Management
    if "management" in report_data:
        st.subheader("👥 Management")
        st.write(clean_report_text(report_data["management"]))

    # Investment Recommendation
    if "recommendation" in report_data:
        st.subheader("🎯 Investment Recommendation")
        st.write(clean_report_text(report_data["recommendation"]))


def display_chatbot():
    """Display chatbot Q&A interface."""
    st.markdown("---")
    st.markdown("### 💬 Ask Questions About This IPO")

    # Display chat history
    if st.session_state.chat_history:
        st.markdown("#### Chat History")
        for i, (q, a) in enumerate(st.session_state.chat_history):
            with st.container():
                st.markdown(f"**Q{i+1}:** {q}")
                st.markdown(f"**A{i+1}:** {a}")
                st.markdown("")

    # Question input
    col1, col2 = st.columns([4, 1])

    with col1:
        question = st.text_input(
            "Your question:",
            key="question_input",
            placeholder="e.g., What are the major revenue sources?",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Align button
        ask_button = st.button("Ask", type="primary")

    if ask_button and question:
        with st.spinner("Getting answer..."):
            result = ask_question(st.session_state.analyzed_company, question)

            if result["status"] == "success":
                answer = result["data"].get("answer", "No answer available")
                st.session_state.chat_history.append((question, answer))
                st.rerun()
            else:
                st.error(f"Error: {result.get('message', 'Unknown error')}")


# Main UI
st.title("📊 XIPO – IPO RHP Analyzer")
st.markdown("Analyze IPO prospectuses with AI-powered insights and financial health scoring")

# Developer Mode Toggle
st.session_state.developer_mode = st.checkbox(
    "🔧 Developer Mode (show raw backend response)",
    value=False,
    key="developer_mode_checkbox"
)

# Company input section
st.markdown("---")
col1, col2 = st.columns([3, 1])

with col1:
    company_name = st.text_input(
        "Enter Company Name:",
        placeholder="e.g., Awfis, Meesho, Lenskart",
        key="company_input",
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)  # Align button
    analyze_button = st.button(
        "Analyze IPO",
        type="primary",
        disabled=st.session_state.is_analyzing,
    )

# Handle analysis
if analyze_button and company_name:
    # Prevent duplicate requests
    if st.session_state.is_analyzing:
        st.warning("⏳ Analysis already in progress...")
    else:
        # Set analyzing flag
        st.session_state.is_analyzing = True

        try:
            with st.spinner(f"Analyzing {company_name.strip()}..."):
                result = analyze_company(company_name)

                # Store debug info
                st.session_state.debug_response = result.get("debug")

                if result["status"] == "success":
                    st.session_state.analyzed_company = company_name.strip()
                    st.session_state.analysis_result = result["data"]
                    st.session_state.chat_history = []  # Reset chat history
                    st.success(f"✓ Analysis complete for {company_name.strip()}")
                    st.rerun()

                elif result["status"] == "not_found":
                    # Clear old results when searching for new company
                    st.session_state.analyzed_company = None
                    st.session_state.analysis_result = None
                    st.session_state.chat_history = []

                    data = result.get("data", {})
                    st.error("❌ No strong match found for this company")

                    # Show suggestions if available
                    if "top_matches" in data and data["top_matches"]:
                        st.markdown("**Did you mean one of these?**")
                        for match in data["top_matches"][:5]:
                            st.markdown(f"- {match.get('title', 'Unknown')} (score: {match.get('score', 0):.2f})")

                    # Show debug info only in developer mode
                    if st.session_state.developer_mode and st.session_state.debug_response:
                        with st.expander("🔍 Debug: Backend Response"):
                            st.write("**Status Code:**", st.session_state.debug_response.get("status_code"))
                            st.write("**URL:**", st.session_state.debug_response.get("url"))
                            if "response_json" in st.session_state.debug_response:
                                st.json(st.session_state.debug_response["response_json"])
                            else:
                                st.code(st.session_state.debug_response.get("response_text", "No response"))

                else:
                    # Clear old results on error
                    st.session_state.analyzed_company = None
                    st.session_state.analysis_result = None
                    st.session_state.chat_history = []

                    status_code = result.get("status_code", "Unknown")
                    message = result.get("message", "Unknown error")
                    st.error(f"❌ Error {status_code}")
                    
                    # Only show raw code in dev mode
                    if st.session_state.developer_mode:
                        st.code(message, language=None)

                    # Show debug info only in developer mode
                    if st.session_state.developer_mode and st.session_state.debug_response:
                        with st.expander("🔍 Debug: Backend Response"):
                            st.write("**Status Code:**", st.session_state.debug_response.get("status_code"))
                            st.write("**URL:**", st.session_state.debug_response.get("url"))
                            if "response_json" in st.session_state.debug_response:
                                st.json(st.session_state.debug_response["response_json"])
                            else:
                                st.code(st.session_state.debug_response.get("response_text", "No response"))
        finally:
            # Always reset analyzing flag
            st.session_state.is_analyzing = False

# Display results if available
if st.session_state.analysis_result and st.session_state.analyzed_company:
    st.markdown("---")

    data = st.session_state.analysis_result

    # Display health score
    if "health_score" in data and data["health_score"]:
        display_health_score(data["health_score"])
        st.markdown("---")

    # Display report with fallback logic
    report_data = None
    for k in ["report", "analysis_report", "analysis", "ipo_report", "final_report"]:
        if k in data and data[k]:
            report_data = data[k]
            break

    if report_data:
        display_report(report_data)
    else:
        st.warning("⚠️ Report not available")

    # Developer mode: show raw backend response in expander
    if st.session_state.developer_mode:
        st.markdown("---")
        with st.expander("🔍 Developer Mode: Raw Backend Response"):
            st.json(data)

    # Display chatbot
    if st.session_state.analyzed_company:
        display_chatbot()

# Footer
st.markdown("---")
st.caption("XIPO - IPO RHP Analyzer | Powered by FastAPI + Streamlit")
