import os
import json
from flask import Flask, request, session, redirect, url_for

import openai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

openai.api_key = os.environ.get("OPENAI_API_KEY")

INDEX_HTML = '''
<h1>SAT Prep Quiz</h1>
<form action="/start" method="post">
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
'''

@app.route('/', methods=['GET'])
def index():
    return INDEX_HTML

@app.route('/start', methods=['POST'])
def start_quiz():
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
                model="gpt-4",  # GPT 4.1 mini placeholder
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"},
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
    session['index'] = 0
    session['score'] = 0
    return redirect(url_for('question'))

@app.route('/question', methods=['GET'])
def question():
    idx = session.get('index', 0)
    questions = session.get('questions')
    if not questions or idx >= len(questions):
        return redirect(url_for('results'))

    q = questions[idx]
    html = '<h1 style="font-size:2em">{}</h1>'.format(q['question'])
    html += '<form action="/answer" method="post">'
    for choice in q['choices']:
        html += f'<label><input type="radio" name="choice" value="{choice}" required> {choice}</label><br>'
    html += '<button type="submit">Next</button></form>'
    return html


@app.route('/answer', methods=['POST'])
def answer():
    choice = request.form.get('choice')
    idx = session.get('index', 0)
    questions = session.get('questions')
    if questions and idx < len(questions):
        correct = questions[idx]['answer']
        if choice == correct:
            session['score'] = session.get('score', 0) + 1
        session['index'] = idx + 1
    return redirect(url_for('question'))


@app.route('/results', methods=['GET'])
def results():
    questions = session.get('questions') or []
    score_value = session.get('score', 0)
    total = len(questions)
    return f'You scored {score_value} out of {total}.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
