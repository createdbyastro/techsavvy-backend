from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import re
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow requests from your website

DB_PATH = "techsavvy.db"

# ── Database setup ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                email     TEXT UNIQUE NOT NULL,
                source    TEXT DEFAULT 'website',
                signed_up TEXT DEFAULT (datetime('now'))
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT,
                email      TEXT NOT NULL,
                message    TEXT NOT NULL,
                sent_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        db.commit()
    print("✅ Database ready.")

def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

# ── Routes ───────────────────────────────────────────────────────

@app.route("/")
def home():
    return jsonify({"status": "TechSavvy API is running 🚀"})

# POST /subscribe — save an email signup
@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required."}), 400
    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO subscribers (email) VALUES (?)", (email,)
            )
            db.commit()
        return jsonify({"message": f"Thanks! {email} has been subscribed. 🎉"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "You're already subscribed!"}), 200

# POST /contact — save a contact form message
@app.route("/contact", methods=["POST"])
def contact():
    data = request.get_json()
    name    = (data or {}).get("name", "").strip()
    email   = (data or {}).get("email", "").strip().lower()
    message = (data or {}).get("message", "").strip()

    if not email or not message:
        return jsonify({"error": "Email and message are required."}), 400
    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    with get_db() as db:
        db.execute(
            "INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)",
            (name, email, message)
        )
        db.commit()
    return jsonify({"message": "Message received! We'll be in touch soon. 👍"}), 201

# GET /admin/subscribers — view all subscribers (protect this in production!)
@app.route("/admin/subscribers", methods=["GET"])
def list_subscribers():
    secret = request.args.get("key")
    if secret != os.environ.get("ADMIN_KEY", "techsavvy2025"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as db:
        rows = db.execute(
            "SELECT id, email, source, signed_up FROM subscribers ORDER BY signed_up DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])

# GET /admin/messages — view all contact messages
@app.route("/admin/messages", methods=["GET"])
def list_messages():
    secret = request.args.get("key")
    if secret != os.environ.get("ADMIN_KEY", "techsavvy2025"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, email, message, sent_at FROM contact_messages ORDER BY sent_at DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])

# GET /admin/export — download subscribers as CSV
@app.route("/admin/export", methods=["GET"])
def export_csv():
    secret = request.args.get("key")
    if secret != os.environ.get("ADMIN_KEY", "techsavvy2025"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as db:
        rows = db.execute(
            "SELECT email, source, signed_up FROM subscribers ORDER BY signed_up DESC"
        ).fetchall()

    lines = ["email,source,signed_up"]
    for r in rows:
        lines.append(f"{r['email']},{r['source']},{r['signed_up']}")
    csv_data = "\n".join(lines)

    from flask import Response
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscribers.csv"}
    )

# ── Start ────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("🌐 TechSavvy backend running on http://localhost:5000")
    print("📋 View subscribers: http://localhost:5000/admin/subscribers?key=techsavvy2025")
    app.run(debug=True, port=5000)
