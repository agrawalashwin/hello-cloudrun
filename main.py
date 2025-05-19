import os
import json
import logging
from flask import Flask, request, redirect, session, url_for
import openai

# Set up Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set up OpenAI client (new SDK pattern)
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# HTML for quiz home page
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

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        json_text = response.choices[0].message.content.strip()
        logging.debug("Raw OpenAI response:\n%s", json_text)

        # Clean up triple backticks and optional ```json block
        if json_text.startswith("```"):
            json_text = json_text.strip("` \n")
            if json_text.startswith("json"):
                json_text = json_text[4:].lstrip()

        try:
            questions = json.loads(json_text)
        except json.JSONDecodeError:
            return f"<pre>Invalid JSON from OpenAI:\n{json_text}</pre>", 500

    except Exception as e:
        logging.exception("Failed to generate questions")
        return f"<pre>OpenAI error: {e}</pre>", 500

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
    html += f'<h1>Question {index + 1}</h1>'
    html += '<form action="/answer" method="post">'
    html += f'<p>{q["question"]}</p>'
    for choice in q["choices"]:
        html += (
            f'<label><input type="radio" name="choice" value="{choice}" '
            f'required> {choice}</label><br>'
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
