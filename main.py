import os
import json
import logging
from flask import Flask, request, redirect, session, url_for

import openai


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")

openai.api_key = os.environ.get("OPENAI_API_KEY")
logging.basicConfig(level=logging.INFO)

INDEX_HTML = '''
<style>
  body { font-family: Arial, sans-serif; margin: 2em; }
  label, button { font-size: 1.2em; }
  input, select { font-size: 1em; }
</style>
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
def start():
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
                model="gpt-4.1-mini-2025-04-14",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            json_text = response.choices[0].message["content"]
            questions = json.loads(json_text)
        except Exception as e:
            logging.exception("Failed to generate questions")
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

@app.route('/question')
def question():
    questions = session.get('questions')
    index = session.get('index', 0)
    if questions is None or index is None:
        return redirect(url_for('index'))
    if index >= len(questions):
        return redirect(url_for('result'))

    q = questions[index]
    html = '<style>p{font-size:1.4em;} label{font-size:1.2em;}</style>'
    html += '<h1>Question {}</h1>'.format(index + 1)
    html += '<form action="/answer" method="post">'
    html += '<p>{}</p>'.format(q['question'])
    for choice in q['choices']:
        html += (
            f'<label><input type="radio" name="choice" value="{choice}" ' +
            'required> {} </label><br>'.format(choice)
        )
    html += '<button type="submit">Submit</button></form>'
    return html


@app.route('/answer', methods=['POST'])
def answer():
    questions = session.get('questions')
    index = session.get('index', 0)
    if questions is None or index is None:
        return redirect(url_for('index'))
    if index < len(questions):
        choice = request.form.get('choice')
        if choice == questions[index]['answer']:
            session['score'] = session.get('score', 0) + 1
        session['index'] = index + 1
    return redirect(url_for('question'))


@app.route('/result')
def result():
    questions = session.get('questions') or []
    score_value = session.get('score', 0)
    total = len(questions)
    session.clear()
    return f'<h1>Your Score: {score_value} / {total}</h1>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
