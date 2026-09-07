import json
import os

from flask import Blueprint, Response, jsonify, request, stream_with_context

from chat import get_ai_response, stream_ai_response
from config import MODEL_CONTEXT_WINDOW
from document_store import clear_document, get_document_status, load_document
from exceptions import (
    LLMAPIError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    StructuredOutputError,
)
from llm_client import get_structured_response
from logger import logger
from models import MessageAnalysis

chat_bp = Blueprint("chat", __name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = (".docx", ".pdf")


# ---------------------------------------------------------------------
# Error handling helpers
# ---------------------------------------------------------------------
def _status_for(exc: LLMError) -> int:
    if isinstance(exc, LLMTimeoutError):
        return 504
    if isinstance(exc, LLMRateLimitError):
        return 429
    if isinstance(exc, LLMConnectionError):
        return 502
    if isinstance(exc, StructuredOutputError):
        return 502
    if isinstance(exc, LLMAPIError):
        return 502
    return 500


@chat_bp.route("/upload", methods=["POST"])
def upload_document():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = file.filename
    lowered = filename.lower()

    if not lowered.endswith(ALLOWED_EXTENSIONS):
        return jsonify({
            "error": "Only .docx and .pdf files are supported"
        }), 400

    extension = ".pdf" if lowered.endswith(".pdf") else ".docx"
    file_path = os.path.join(UPLOAD_DIR, f"active_document{extension}")

    file.save(file_path)

    try:
        load_document(file_path, original_filename=filename)
    except ValueError as e:
        logger.warning("Document upload rejected (%s): %s", filename, e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Could not read uploaded document: %s", filename)
        return jsonify({
            "error": f"Could not read document: {str(e)}"
        }), 400

    logger.info("Document indexed: %s", filename)

    return jsonify({
        "message": "Document uploaded and indexed successfully",
        "document": get_document_status(),
    })


@chat_bp.route("/document/status", methods=["GET"])
def document_status():
    return jsonify(get_document_status())


@chat_bp.route("/document", methods=["DELETE"])
def remove_document():
    clear_document()
    logger.info("Document cleared")
    return jsonify({"message": "Document cleared", "document": get_document_status()})


@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()

        if not message:
            return jsonify({"error": "Message cannot be empty."}), 400

        logger.info("USER: %s", message)
        result = get_ai_response(message)
        logger.info("AI: %s", result["response"])

        return jsonify({
            "response": result["response"],
            "used_rag": result["used_rag"],
            "sources": result["sources"],
            "tools_used": result["tools_used"],
            "token_usage": result["token_usage"],
        })

    except LLMError as e:
        logger.error("Chat request failed: %s", e)
        return jsonify({"error": str(e)}), _status_for(e)

    except Exception as e:
        logger.exception("Unexpected error in /chat")
        return jsonify({"error": "An unexpected error occurred."}), 500


@chat_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """
    Server-Sent-Events endpoint. Each event is a line of the form
    'data: <json>\\n\\n', where the JSON payload matches the event
    dicts yielded by chat.stream_ai_response().
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    logger.info("USER (stream): %s", message)

    def event_stream():
        for event in stream_ai_response(message):
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering, if any
        },
    )


@chat_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    Structured-output demo: classifies a message's sentiment, priority,
    and category as a validated JSON object (see models.MessageAnalysis).
    """
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()

        if not message:
            return jsonify({"error": "Message cannot be empty."}), 400

        analysis = get_structured_response(message, MessageAnalysis)
        return jsonify(analysis.model_dump())

    except LLMError as e:
        logger.error("Analyze request failed: %s", e)
        return jsonify({"error": str(e)}), _status_for(e)

    except Exception as e:
        logger.exception("Unexpected error in /analyze")
        return jsonify({"error": "An unexpected error occurred."}), 500


@chat_bp.route("/limits", methods=["GET"])
def limits():
    """Static info the frontend uses to render the token-limit bar
    before any message has been sent."""
    return jsonify({"context_window": MODEL_CONTEXT_WINDOW})