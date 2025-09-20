# api/index.py
# This file exposes your Flask app to Vercel's Python runtime.
# It should export a variable named `app` which is the Flask app instance.

import sys
import traceback

try:
    # try import your app object from the repo root `app.py`
    # If your app uses a factory like `create_app()`, import + call that instead.
    from app import app   # <-- adjust if your Flask instance is named differently
except Exception as exc:
    # If import fails, expose a minimal fallback app to help debugging in Vercel logs.
    from flask import Flask, Response
    fallback = Flask(__name__)

    @fallback.route("/", defaults={"path": ""})
    @fallback.route("/<path:path>")
    def _err(path):
        tb = traceback.format_exc()
        msg = (
            "Failed to import your Flask app.\n\n"
            "Exception:\n"
            f"{tb}\n\n"
            "Check that app.py defines `app = Flask(__name__)` or adjust api/index.py to import properly."
        )
        return Response(msg, status=500, mimetype="text/plain")
    app = fallback
