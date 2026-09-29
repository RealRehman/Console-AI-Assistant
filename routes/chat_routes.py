import json
import os
import uuid

from flask import Blueprint, Response, jsonify, request, stream_with_context

from chat import clear_conversation, get_ai_response, stream_ai_response
from config import MODEL_CONTEXT_WINDOW
from document_store import (
    clear_all_documents,
    get_document_status,
    load_document,
    remove_document,
)
from rag.parsers import SUPPORTED_EXTENSIONS
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
    """
    Adds a document to the library (Week 7: PDF, DOCX, TXT, Markdown).
    Unlike earlier weeks, this does NOT replace previously loaded
    documents -- multiple documents can be loaded at once.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = file.filename
    lowered = filename.lower()

    if not lowered.endswith(SUPPORTED_EXTENSIONS):
        return jsonify({
            "error": f"Unsupported file type. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        }), 400

    extension = os.path.splitext(lowered)[1]
    # Unique temp filename -- multiple documents can be in flight/stored
    # at once, so we can no longer reuse one fixed "active_document" path.
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{extension}")
    file.save(file_path)

    try:
        doc = load_document(file_path, original_filename=filename)
    except ValueError as e:
        logger.warning("Document upload rejected (%s): %s", filename, e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Could not read uploaded document: %s", filename)
        return jsonify({"error": f"Could not read document: {str(e)}"}), 400
    finally:
        # The extracted text is already indexed in Qdrant; the raw
        # upload on disk isn't needed after ingestion.
        try:
            os.remove(file_path)
        except OSError:
            pass

    logger.info("Document indexed: %s (%s chunks)", filename, doc["chunk_count"])

    return jsonify({
        "message": "Document uploaded and indexed successfully",
        "document": doc,
        "library": get_document_status(),
    })


@chat_bp.route("/document/status", methods=["GET"])
def document_status():
    return jsonify(get_document_status())


@chat_bp.route("/document/<doc_id>", methods=["DELETE"])
def remove_one_document(doc_id):
    try:
        remove_document(doc_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    logger.info("Document removed: %s", doc_id)
    return jsonify({"message": "Document removed", "library": get_document_status()})


@chat_bp.route("/documents", methods=["DELETE"])
def remove_all_documents():
    clear_all_documents()
    logger.info("All documents cleared")
    return jsonify({"message": "All documents cleared", "library": get_document_status()})


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

        return jsonify(result)

    except LLMError as e:
        logger.error("Chat request failed: %s", e)
        return jsonify({"error": str(e)}), _status_for(e)

    except Exception:
        logger.exception("Unexpected error in /chat")
        return jsonify({"error": "An unexpected error occurred."}), 500


@chat_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@chat_bp.route("/chat/clear", methods=["POST"])
def chat_clear():
    clear_conversation()
    return jsonify({"message": "Conversation cleared"})


@chat_bp.route("/analyze", methods=["POST"])
def analyze():
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

    except Exception:
        logger.exception("Unexpected error in /analyze")
        return jsonify({"error": "An unexpected error occurred."}), 500


@chat_bp.route("/limits", methods=["GET"])
def limits():
    return jsonify({"context_window": MODEL_CONTEXT_WINDOW})