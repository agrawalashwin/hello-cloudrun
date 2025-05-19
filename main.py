import os
import json
from flask import Flask, request, session, redirect, render_template_string

import openai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

openai.api_key = os.environ.get("OPENAI_API_KEY")

INDEX_HTML = """
<!doctype html>
<html>
<head>
<style>
body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
label, select, input, button { font-size: 1.2em; margin-top: 10px; }
</style>
</head>
<body>
<h1>SAT Prep Quiz</h1>
<form action="/quiz" method="post">
  <label>Topic:
    <select name="topic">
      <option value="language">Language</option>
      <option value="math">Math</option>
    </select>
  </label><br>
  <label>Grade:
    <input type="number" name="grade" min="1" max="12" required>
  </label><br>
  <label>Number of questions:
    <input type="number" name="num" min="1" max="10" required>
  </label><br>
  <button type="submit">Start Quiz</button>
</form>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return INDEX_HTML

@app.route('/quiz', methods=['POST'])
def quiz():
    topic = request.form.get('topic', 'language')
    grade = request.form.get('grade', '3')
    num = int(request.form.get('num', 1))

    prompt = (
        "Generate a short SAT practice quiz for a grade {grade} student. "
        "Focus on {topic}. Provide {num} multiple choice questions. "
        "Return JSON formatted as a list of objects with fields 'question', "
        "'choices' (list of options), and 'answer' (the correct option)."
    ).format(grade=grade, topic=topic, num=num)

    if openai.api_key:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # GPT-4.1 equivalent
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            json_text = response.choices[0].message["content"]
            questions = json.loads(json_text)
        except Exception:
            return "Failed to generate quiz", 500
    else:
        # Fallback quiz if no API key is provided
        questions = [
            {
                "question": "Sample question?",
                "choices": ["A", "B", "C", "D"],
                "answer": "A",
            }
            for _ in range(num)
        ]

    session['questions'] = questions
    session['current'] = 0
    session['score'] = 0
    return redirect('/question')


@app.route('/question', methods=['GET'])
def question():
    idx = session.get('current', 0)
    questions = session.get('questions', [])
    if idx >= len(questions):
        return redirect('/result')
    q = questions[idx]
    question_html = """
    <!doctype html>
    <html>
    <head>
    <style>
    body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
    .question { font-size: 2em; margin-bottom: 20px; }
    label { font-size: 1.5em; }
    </style>
    </head>
    <body>
    <h1>Question {{ num }} of {{ total }}</h1>
    <form action="/answer" method="post">
      <p class="question">{{ q['question'] }}</p>
      {% for choice in q['choices'] %}
        <label><input type="radio" name="choice" value="{{ choice }}" required> {{ choice }}</label><br>
      {% endfor %}
      <button type="submit">Submit</button>
    </form>
    </body>
    </html>
    """
    return render_template_string(
        question_html,
        q=q,
        num=idx + 1,
        total=len(questions),
    )


@app.route('/answer', methods=['POST'])
def answer():
    idx = session.get('current', 0)
    questions = session.get('questions', [])
    if idx >= len(questions):
        return redirect('/result')
    choice = request.form.get('choice')
    if choice == questions[idx]['answer']:
        session['score'] = session.get('score', 0) + 1
    session['current'] = idx + 1
    if session['current'] >= len(questions):
        return redirect('/result')
    return redirect('/question')


@app.route('/result', methods=['GET'])
def result():
    score_value = session.get('score', 0)
    total = len(session.get('questions', []))
    session.clear()
    result_html = """
    <!doctype html>
    <html>
    <head>
    <style>
    body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
    .score { font-size: 2em; }
    </style>
    </head>
    <body>
    <h1>Quiz Complete</h1>
    <p class="score">You scored {{ score }} out of {{ total }}.</p>
    <a href="/">Start a new quiz</a>
    </body>
    </html>
    """
    return render_template_string(result_html, score=score_value, total=total)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
