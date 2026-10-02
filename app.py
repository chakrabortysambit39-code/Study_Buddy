import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq
from sqlalchemy import create_engine, text

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "study-buddy-dev-secret-change-me")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///study_buddy.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

def make_engine(url):
    return create_engine(url, pool_pre_ping=True)

def init_database():
    global engine, database_ok
    try:
        engine = make_engine(DATABASE_URL)
        with engine.begin() as conn:
            conn.execute(text("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                mode VARCHAR(30) NOT NULL,
                created_at TIMESTAMP NOT NULL
            )""") if "sqlite" not in DATABASE_URL else text("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""))
        database_ok = True
    except Exception as exc:
        print(f"Database unavailable: {exc}")
        # Keep the web app alive while Render's external database is unavailable.
        engine = make_engine("sqlite:///study_buddy_fallback.db")
        with engine.begin() as conn:
            conn.execute(text("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""))
        database_ok = False

init_database()

groq_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=groq_key) if groq_key else None
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM = """You are Study Buddy, a warm, accurate AI tutor.
Teach rather than simply give answers. Use clear language suitable for a school student.
Break difficult ideas into small steps, use examples and short summaries.
Never pretend to know something you do not know. For schoolwork, encourage understanding.
For quizzes, use numbered questions with four options (A-D) and an answer key.
For flashcards, use concise Front: / Back: pairs.
"""

MODES = {
    "tutor": "Act as a patient personal tutor. Explain the concept and then give one quick check question.",
    "explain": "Explain the topic in very simple language, using an analogy and a tiny example.",
    "quiz": "Create a short 5-question quiz. Use four options (A-D), then provide an answer key.",
    "flashcards": "Create 8 useful flashcards. Format each as Front: ... Back: ...",
    "exam": "Act as an exam coach. Give key points, common mistakes, a mini practice question, and a final memory trick."
}

@app.get("/")
def home():
    return render_template(
        "index.html",
        did_agent_id=os.getenv("DID_AGENT_ID", ""),
        did_client_key=os.getenv("DID_CLIENT_KEY", "")
    )

@app.get("/health")
def health():
    return jsonify({"status": "ok", "groq": bool(groq_key), "database": database_ok,
                    "did_agent": bool(os.getenv("DID_AGENT_ID") and os.getenv("DID_CLIENT_KEY"))})

@app.get("/api/history")
def history():
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT role, content, mode FROM messages ORDER BY id DESC LIMIT 50"
        )).mappings().all()
    return jsonify({"messages": list(reversed([dict(r) for r in rows]))})

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    mode = data.get("mode", "tutor")
    history = data.get("history", [])[-10:]

    if not message:
        return jsonify({"error": "Please enter a question."}), 400
    if not client:
        return jsonify({"error": "GROQ_API_KEY is not configured in Render Environment."}), 500

    messages = [{"role": "system", "content": SYSTEM + "\n\nCURRENT MODE:\n" + MODES.get(mode, MODES["tutor"])}]
    for item in history:
        if item.get("role") in ("user", "assistant") and item.get("content"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.5, max_tokens=1200
        )
        answer = response.choices[0].message.content
        now = datetime.now(timezone.utc).isoformat()
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO messages (role, content, mode, created_at) VALUES (:r,:c,:m,:t)"),
                         {"r":"user","c":message,"m":mode,"t":now})
            conn.execute(text("INSERT INTO messages (role, content, mode, created_at) VALUES (:r,:c,:m,:t)"),
                         {"r":"assistant","c":answer,"m":mode,"t":now})
        return jsonify({"answer": answer, "model": MODEL})
    except Exception as exc:
        return jsonify({"error": f"AI request failed: {exc}"}), 500

@app.post("/api/clear-history")
def clear_history():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM messages"))
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
