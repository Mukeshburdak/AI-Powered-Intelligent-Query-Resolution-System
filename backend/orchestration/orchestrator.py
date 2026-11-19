
import re
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.config import SAMPLE_DOCUMENTS_DIR

from backend.agents.query_agent import QueryAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.response_agent import ResponseAgent
from backend.agents.clarification_agent import ClarificationAgent
from backend.agents.memory_agent import MemoryAgent
from backend.agents.structured_data_agent import structured_data_agent


# ---------------------------------------------------------
# Initialize all six agents
# ---------------------------------------------------------

query_agent = QueryAgent()
retrieval_agent = RetrievalAgent()
response_agent = ResponseAgent()
clarification_agent = ClarificationAgent()
memory_agent = MemoryAgent()


# ---------------------------------------------------------
# Structured Data Query Detection
# ---------------------------------------------------------


def is_structured_data_question(question: str) -> bool:
    """
    Identify CSV analytics questions while keeping programming
    and document-related questions on the RAG pipeline.
    """

    text = question.lower().strip()

    # Programming and document context should use RAG.
    document_context_patterns = [
        r"\bprogram\b",
        r"\bsource code\b",
        r"\bcode snippet\b",
        r"\bc program\b",
        r"\bfunction\b",
        r"\bfunction call\b",
        r"\bfunction definition\b",
        r"\bcode\b",
        r"\boutput\b",
        r"\bcompiler\b",
        r"\bexecute\b",
        r"\bpdf\b",
        r"\bdocument\b",
        r"\buploaded file\b",
        r"\bprovided file\b",
        r"\bgiven file\b",
    ]

    if any(
        re.search(pattern, text)
        for pattern in document_context_patterns
    ):
        return False

    analytics_patterns = [
        r"\bhow many\b",
        r"\bhow much\b",
        r"\bcount\b",
        r"\bnumber of\b",
        r"\btotal\b",
        r"\baverage\b",
        r"\bmean\b",
        r"\bmaximum\b",
        r"\bminimum\b",
        r"\bmax\b",
        r"\bmin\b",
        r"\bhighest\b",
        r"\blargest\b",
        r"\blowest\b",
        r"\bsmallest\b",
        r"\bsum\b",
    ]

    category_patterns = [
        r"\bmales?\b",
        r"\bfemales?\b",
        r"\bmen\b",
        r"\bwomen\b",
        r"\bsmokers?\b",
        r"\bnon smokers?\b",
        r"\bsouthwest\b",
        r"\bsoutheast\b",
        r"\bnorthwest\b",
        r"\bnortheast\b",
    ]

    return (
        any(re.search(pattern, text) for pattern in analytics_patterns)
        or any(re.search(pattern, text) for pattern in category_patterns)
    )


# ---------------------------------------------------------
# Find CSV Files Belonging to the Logged-in User
# ---------------------------------------------------------

def find_user_csv_files(user_id: int) -> list[Path]:

    user_directory = SAMPLE_DOCUMENTS_DIR / str(user_id)

    if not user_directory.exists():
        return []

    return sorted(user_directory.glob("*.csv"))


def find_user_document(
    user_id: int,
    document_id: str,
) -> Path | None:
    """Resolve a selected document inside the logged-in user's directory."""

    user_directory = (
        SAMPLE_DOCUMENTS_DIR / str(user_id)
    ).resolve()

    # Reject paths instead of accepting arbitrary filesystem locations.
    if not document_id or Path(document_id).name != document_id:
        return None

    candidate = (user_directory / document_id).resolve()

    try:
        candidate.relative_to(user_directory)
    except ValueError:
        return None

    if not candidate.is_file():
        return None

    return candidate

# ---------------------------------------------------------
# Select the Correct CSV Dataset
# ---------------------------------------------------------

def select_csv_file(
    question: str,
    csv_files: list[Path],
) -> Path | None:

    if not csv_files:
        return None

    grouped_files = {}

    for csv_file in csv_files:
        original_name = csv_file.name.split("_", 1)[-1].lower()
        grouped_files.setdefault(original_name, []).append(csv_file)

    # Select the latest upload if all files have the same name.
    if len(grouped_files) == 1:
        return max(
            csv_files,
            key=lambda file: file.stat().st_mtime,
        )

    # Match an explicitly mentioned dataset filename.
    question_lower = question.lower()

    for original_name, files in grouped_files.items():

        if original_name in question_lower:
            return max(
                files,
                key=lambda file: file.stat().st_mtime,
            )

    return None


# ---------------------------------------------------------
# Save Conversation Messages
# ---------------------------------------------------------

def save_conversation(
    conversation_id: str,
    user_id: int | None,
    db: Session | None,
    question: str,
    answer: str,
    agents: dict,
):

    if user_id is None or db is None:
        return

    try:

        memory_agent.save_message(
            conversation_id,
            user_id,
            "user",
            question,
            db,
        )

        memory_agent.save_message(
            conversation_id,
            user_id,
            "assistant",
            answer,
            db,
        )

        agents["conversation_memory"]["status"] = "completed"

    except Exception:

        db.rollback()
        agents["conversation_memory"]["status"] = "error"


# ---------------------------------------------------------
# Main Query Orchestrator
# ---------------------------------------------------------

def answer_query(
    question: str,
    conversation_id: str | None = None,
    *,
    user_id: int | None = None,
    db: Session | None = None,
    document_id: str | None = None,
) -> dict:

    conversation_id = conversation_id or str(uuid.uuid4())

    normalized = query_agent.prepare(question)

    # -----------------------------------------------------
    # Initialize Agent Monitoring
    # -----------------------------------------------------

    agents = {

        "query_understanding": {
            "name": "Query Understanding Agent",
            "status": "running",
            "description": "Analyzes and classifies the user query.",
        },

        "retrieval": {
            "name": "Retrieval Agent",
            "status": "not_started",
            "description": "Searches relevant document chunks using FAISS.",
        },

        "response_generation": {
            "name": "Response Generation Agent",
            "status": "not_started",
            "description": "Generates grounded answers using Gemini.",
        },

        "clarification": {
            "name": "Clarification Agent",
            "status": "not_started",
            "description": "Checks whether the query needs clarification.",
        },

        "conversation_memory": {
            "name": "Conversation Memory Agent",
            "status": "not_started",
            "description": "Retrieves and stores conversation history.",
        },

        "structured_data": {
            "name": "Structured Data Agent",
            "status": "not_started",
            "description": "Performs exact calculations and analytics on uploaded CSV datasets.",
        },
    }

    # -----------------------------------------------------
    # Step 1: Handle Empty Questions
    # -----------------------------------------------------

    if not normalized:

        agents["query_understanding"]["status"] = "completed"
        agents["query_understanding"]["intent"] = "ambiguous"

        agents["clarification"]["status"] = "completed"

        agents["conversation_memory"]["status"] = "completed_no_history"

        return {
            "conversation_id": conversation_id,
            "answer": "Please enter a question so I can help you.",
            "sources": [],
            "confidence": 0.0,
            "needs_clarification": True,
            "question_type": "ambiguous",
            "agents": agents,
        }

    # -----------------------------------------------------
    # Step 2: Query Understanding Agent
    # -----------------------------------------------------

    classification = query_agent.classify(normalized)


    # Validate the selected document belongs to the logged-in user.
    selected_document = None

    if document_id is not None:
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication is required to select a document.",
            )

        selected_document = find_user_document(
            user_id,
            document_id,
        )

        if selected_document is None:
            raise HTTPException(
                status_code=404,
                detail="Selected document was not found in your account.",
            )


    agents["query_understanding"].update({
        "status": "completed",
        "intent": classification["intent"],
    })

    # -----------------------------------------------------
    # Step 3: Conversation Memory Agent
    # -----------------------------------------------------

    context = []

    try:

        if user_id is not None and db is not None:

            context = memory_agent.get_context(
                conversation_id=conversation_id,
                user_id=user_id,
                db=db,
            )

        agents["conversation_memory"]["status"] = (
            "completed" if context else "completed_no_history"
        )

    except Exception:

        agents["conversation_memory"]["status"] = "error"
        context = []

    # -----------------------------------------------------
    # Step 4: Clarification Agent
    # -----------------------------------------------------

    agents["clarification"]["status"] = "running"

    needs_clarification = (
        classification["needs_clarification"]
        or clarification_agent.needs_clarification(normalized)
    )

    if needs_clarification:

        answer = "Could you please provide a more specific question?"

        agents["clarification"]["status"] = "completed"

        save_conversation(
            conversation_id,
            user_id,
            db,
            normalized,
            answer,
            agents,
        )

        return {
            "conversation_id": conversation_id,
            "answer": answer,
            "sources": [],
            "confidence": 0.0,
            "needs_clarification": True,
            "question_type": classification["question_type"],
            "agents": agents,
        }

    agents["clarification"]["status"] = "completed"

    # -----------------------------------------------------
    # Step 5: Structured Data Agent
    # -----------------------------------------------------

    if is_structured_data_question(normalized):

        agents["structured_data"]["status"] = "running"

        answer = ""
        dataset_filename = None
        rows_analyzed = None

        if user_id is None:

            answer = (
                "Please log in to analyze your uploaded CSV dataset."
            )

            agents["structured_data"]["status"] = "error"

        else:


            csv_files = find_user_csv_files(user_id)

            selected_file = None

            if selected_document is not None:
                if selected_document.suffix.lower() != ".csv":
                    answer = (
                        "The selected document is not a CSV dataset. "
                        "Please select a CSV file to perform structured data analysis."
                    )
                    agents["structured_data"]["status"] = "completed"

                else:
                    selected_file = selected_document

            elif not csv_files:
                answer = (
                    "No CSV dataset was found in your account. "
                    "Please upload a CSV file first."
                )
                agents["structured_data"]["status"] = "completed"

            else:
                selected_file = select_csv_file(
                    normalized,
                    csv_files,
                )

                if selected_file is None:
                    filenames = sorted(set(
                        file.name.split("_", 1)[-1]
                        for file in csv_files
                    ))

                    answer = (
                        "Multiple CSV datasets were found. "
                        "Please specify which dataset you want to analyze: "
                        + ", ".join(filenames)
                    )

                    agents["structured_data"]["status"] = "completed"

            if selected_file is not None:
                try:
                    result = structured_data_agent.answer(
                        normalized,
                        selected_file,
                    )

                    if isinstance(result, dict):
                        answer = result.get("answer", str(result))
                    else:
                        answer = str(result)

                    dataset_filename = selected_file.name.split(
                        "_", 1
                    )[-1]

                    rows_analyzed = len(
                        pd.read_csv(selected_file)
                    )

                    agents["structured_data"]["status"] = "completed"

                except Exception:
                    answer = (
                        "An error occurred while analyzing the CSV dataset. "
                        "Please check the uploaded file and try again."
                    )

                    dataset_filename = None
                    rows_analyzed = None

                    agents["structured_data"]["status"] = "error"


        # Save CSV analysis conversation.
        save_conversation(
            conversation_id,
            user_id,
            db,
            normalized,
            answer,
            agents,
        )

        # Return structured-data response.
        return {
            "conversation_id": conversation_id,
            "answer": answer,
            "sources": [],
            "confidence": None,
            "needs_clarification": False,
            "question_type": "structured_data",
            "dataset_filename": dataset_filename,
            "rows_analyzed": rows_analyzed,
            "agents": agents,
        }

    # -----------------------------------------------------
    # Step 6: Normal Document Retrieval Agent (RAG)
    # -----------------------------------------------------

    agents["retrieval"]["status"] = "running"

    try:

        sources = retrieval_agent.retrieve(
            normalized,
            user_id=user_id,
            document_id=document_id,
        )

        agents["retrieval"]["status"] = "completed"

    except Exception:

        agents["retrieval"]["status"] = "error"
        raise

    # -----------------------------------------------------
    # Step 7: Response Generation Agent
    # -----------------------------------------------------

    agents["response_generation"]["status"] = "running"

    try:

        response = response_agent.respond(
            normalized,
            sources,
            conversation_context=context,
        )

        agents["response_generation"]["status"] = "completed"

    except Exception:

        agents["response_generation"]["status"] = "error"
        raise

    # -----------------------------------------------------
    # Step 8: Save Conversation
    # -----------------------------------------------------

    save_conversation(
        conversation_id,
        user_id,
        db,
        normalized,
        response.get("answer", ""),
        agents,
    )

    # -----------------------------------------------------
    # Step 9: Return Final Response
    # -----------------------------------------------------

    return {
        "conversation_id": conversation_id,
        **response,
        "needs_clarification": False,
        "question_type": classification["question_type"],
        "agents": agents,
    }
