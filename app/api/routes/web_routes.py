"""
app/api/web_routes.py — HTML page routes.
"""
from app.utils._flask_compat import Blueprint, render_template

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    return render_template("index.html")
