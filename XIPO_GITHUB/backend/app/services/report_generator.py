"""
IPO Analysis Report Generator Service
Generates a comprehensive IPO analysis report by asking predefined questions
through the existing RAG pipeline.
"""

from app.services.rag_engine import answer_question


# Predefined questions for each report section
_REPORT_QUESTIONS = {
    "company_overview": "What does this company do? Provide a brief overview of the business.",
    "business_model": "Explain the business model and how the company generates revenue.",
    "objects_of_issue": "What are the objects of the issue? How will the IPO proceeds be used?",
    "strengths": "What are the key strengths and competitive advantages of this company?",
    "key_risks": "What are the major risks and challenges mentioned in the prospectus?",
    "financial_highlights": "Summarize the key financial metrics and performance highlights.",
    "final_verdict": "Provide a brief investment perspective on this IPO. Is it suitable for retail investors? Note: This is not financial advice.",
}


def generate_default_report(company_name: str, top_k: int = 6) -> dict:
    """
    Generate a comprehensive IPO analysis report by asking predefined questions
    through the RAG pipeline.

    Args:
        company_name: Name of the company to analyze.
        top_k: Number of chunks to retrieve per question (default: 6).

    Returns:
        dict with keys:
            - company_name: Name of the company
            - report: Structured report with all sections
    """
    report = {}

    # Ask each question and populate the report
    for section_key, question in _REPORT_QUESTIONS.items():
        try:
            result = answer_question(
                company_name=company_name,
                question=question,
                top_k=top_k,
                debug=False,
                timeout=300,
                retries=1
            )
            answer = result.get("answer", "Not clearly available in the RHP")
            report[section_key] = answer.strip()
        except Exception as e:
            # If any question fails, note it in the report
            report[section_key] = f"Error retrieving information: {str(e)}"

    return {
        "company_name": company_name,
        "report": report,
    }
