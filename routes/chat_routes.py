from flask import Blueprint
from flask import request
from flask import jsonify
from flask import request, jsonify
from document_store import load_document

from chat import get_ai_response


chat_bp = Blueprint("chat", __name__)

# Keeps the running conversation so the AI has context turn to turn.
conversation_history = []


@chat_bp.route("/upload", methods=["POST"])
def upload_document():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = file.filename.lower()

    if not (
        filename.endswith(".docx")
        or filename.endswith(".pdf")
    ):
        return jsonify({
            "error": "Only .docx and .pdf files are supported"
        }), 400

    file_path = f"uploaded_document{'.pdf' if filename.endswith('.pdf') else '.docx'}"

    file.save(file_path)

    try:

        load_document(file_path)

    except Exception as e:

        return jsonify({
            "error": f"Could not read document: {str(e)}"
        }), 400

    return jsonify({
        "message": "Document uploaded successfully"
    })

@chat_bp.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json()

        message = data.get("message", "").strip()

        if not message:

            return jsonify({
                "error": "Message cannot be empty."
            }), 400

        conversation_history.append({
            "role": "user",
            "content": message
        })

        ai_reply = get_ai_response(conversation_history)

        conversation_history.append({
            "role": "assistant",
            "content": ai_reply
        })

        return jsonify({
            "response": ai_reply
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500