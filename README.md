# Study Buddy AI 📚🤖

An AI-powered study companion for students.

## Features
- AI Tutor chat
- Tutor / Explain / Quiz / Flashcards modes
- Simple, student-friendly explanations
- Quiz generation
- Flashcard generation
- Session stats
- Modern responsive UI

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
set GROQ_API_KEY=your_key_here
python app.py
```

Open http://127.0.0.1:5000

For deployment, add `GROQ_API_KEY` as an environment variable.
