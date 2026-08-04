from flask import Blueprint
from flask import render_template


page_bp = Blueprint("page", __name__)


@page_bp.route("/")
def home():

    return render_template("index.html")