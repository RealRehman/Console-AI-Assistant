from flask import Blueprint
from flask import request
from flask import jsonify

from chat import get_ai_response


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json()

        message = data.get("message", "").strip()

        if not message:

            return jsonify({
                "error": "Message cannot be empty."
            }), 400

        ai_reply = get_ai_response(message)

        return jsonify({
            "response": ai_reply
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500