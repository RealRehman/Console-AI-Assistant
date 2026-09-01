import os

from flask import Blueprint, request, jsonify

from document_store import load_document, get_document_status, clear_document
from chat import get_ai_response
from config import MODEL_CONTEXT_WINDOW

chat_bp = Blueprint("chat", __name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = (".docx", ".pdf")


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
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({
            "error": f"Could not read document: {str(e)}"
        }), 400

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
    return jsonify({"message": "Document cleared", "document": get_document_status()})


@chat_bp.route("/chat", methods=["POST"])
def chat():

    try:
        data = request.get_json()

        message = data.get("message", "").strip()

        if not message:
            return jsonify({
                "error": "Message cannot be empty."
            }), 400

        result = get_ai_response(message)

        return jsonify({
            "response": result["response"],
            "used_rag": result["used_rag"],
            "sources": result["sources"],
            "token_usage": result["token_usage"],
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@chat_bp.route("/limits", methods=["GET"])
def limits():
    """Static info the frontend uses to render the token-limit bar
    before any message has been sent."""
    return jsonify({"context_window": MODEL_CONTEXT_WINDOW})
