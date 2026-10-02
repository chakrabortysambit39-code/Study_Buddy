import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None

SYSTEM = """You are Study Buddy, a warm, accurate AI tutor.
Teach rather than simply give answers. Use clear language suitable for a school student.
Break difficult ideas into small steps, use examples and short summaries.
Never pretend to know something you do not know. For schoolwork, encourage understanding.
When asked for a quiz, return numbered questions with four options and put the answer after each question.
When asked for flashcards, return concise Front: / Back: pairs.
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
    return render_template("index.html")

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    mode = data.get("mode", "tutor")
    history = data.get("history", [])[-10:]

    if not message:
        return jsonify({"error": "Please enter a question."}), 400

    if not client:
        return jsonify({"error": "GROQ_API_KEY is not configured. Add it to your environment variables."}), 500

    mode_instruction = MODES.get(mode, MODES["tutor"])
    messages = [{"role": "system", "content": SYSTEM + "\n\nCURRENT MODE:\n" + mode_instruction}]
    for item in history:
        if item.get("role") in ("user", "assistant") and item.get("content"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.5,
            max_tokens=1200,
        )
        return jsonify({"answer": response.choices[0].message.content})
    except Exception as exc:
        return jsonify({"error": f"AI request failed: {exc}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
