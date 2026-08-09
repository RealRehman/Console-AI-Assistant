from flask import Blueprint
from flask import request
from flask import jsonify

from chat import get_ai_response

from conversation_manager import (
    create_conversation,
    load_conversation,
    save_conversation
)


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


        # Get conversation ID from the request
        conversation_id = data.get("conversation_id")


        # Create a new conversation if one doesn't exist
        if not conversation_id:

            conversation_id = create_conversation()


        # Load existing conversation
        messages = load_conversation(conversation_id)


        # Add user message
        messages.append({
        "role": "user",
        "content": message
        })


# Get AI response using conversation history
        ai_reply = get_ai_response(messages)


        # Add AI response
        messages.append({
            "role": "assistant",
            "content": ai_reply
        })


        # Save updated conversation
        save_conversation(
            conversation_id,
            messages
        )


        return jsonify({
            "conversation_id": conversation_id,
            "response": ai_reply
        })


    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500