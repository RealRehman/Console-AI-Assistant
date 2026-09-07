from flask import Flask, jsonify

from routes.page_routes import page_bp
from routes.chat_routes import chat_bp
from logger import logger


app = Flask(__name__)

app.register_blueprint(page_bp)
app.register_blueprint(chat_bp)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    logger.exception("Unhandled server error")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting AI Assistant Flask app")
    app.run(debug=True)