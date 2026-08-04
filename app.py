from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Home Page"


@app.route("/about")
def about():
    return "About AI Assistant"


@app.route("/contact")
def contact():
    return "Contact Page"


if __name__ == "__main__":
    app.run(debug=True)