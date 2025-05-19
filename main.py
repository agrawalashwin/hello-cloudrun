import os
import json
import logging
from flask import Flask, request, redirect, session, url_for
import openai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
logging.basicConfig(level=logging.DEBUG)

# OpenAI SDK
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

INDEX_HTML = '''
<html>
<head>
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #f4f4f8; padding: 2em; text-align: center; }
  .quiz-box { background: white; padding: 2em; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }
  h1 { font-size: 2em; margin-bottom: 0.5em; }
  label, select, input, button { font-size: 1.1em; margin-top: 10px; display: block; width: 100%; padding: 8px; }
  button { background-color: #007BFF; color: white; border: none; border-radius: 6px; cursor: pointer; }
  button:hover { background-color: #0056b3; }
</style>
</head>
<body>
  <div class="quiz-box">
    <h1>SAT Prep Quiz</h1>
    <form action="/start" method="post">
      <label>Topic:
        <select name="topic">
          <option value="language">Language</option>
          <option value="math">Math</option>
        </select>
      </label>
      <label>Grade:
        <input type="number" name="grade" min="1" max="12" required>
      </label>
      <label>Number of questions:
        <input type="number" name="num" min="1" max="10" required>
      </label>
      <button type="submit">Start Quiz</button>
    </form>
  </div>
</body>
</html>
'''

@app.route('/')
def index():
    return INDEX_HTML

@app.route('/start', methods=['POST'])
def start():
    try:
        session.clear()
        topic = request.form.get('topic', 'language')
        grade = request.form.get('grade', '3')
        num = int(request.form.get('num', 1))

        session['topic'] = topic
        session['grade'] = grade
        session['num'] = num
        session['score'] = 0
        session['index'] = 0
        session['difficulty'] = "medium"
        session['questions'] = []

        return redirect(url_for('question'))
    except Exception as e:
        logging.exception("Error in /start")
        return f"<pre>/start error:\n{e}</pre>", 500

@app.route('/question')
def question():
    try:
        index = session.get('index', 0)
        num = session.get('num', 1)
        topic = session.get('topic', 'language')
        grade = session.get('grade', '3')
        difficulty = session.get('difficulty', 'medium')

        if index >= num:
            return redirect(url_for('result'))

        prompt = (
            "Generate 1 {difficulty} SAT-style multiple choice question "
            "for a grade {grade} student focusing on {topic}. "
            "Return JSON with 'question', 'choices' (list), and 'answer'."
        ).format(grade=grade, topic=topic, difficulty=difficulty)

        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw = response.choices[0].message.content.strip()
        logging.debug("GPT raw response:\n%s", raw)

        if raw.startswith("```"):
            raw = raw.strip("` \n")
            if raw.startswith("json"):
                raw = raw[4:].lstrip()

        data = json.loads(raw)
        session['questions'].append(data)

        html = f'''
        <html><head><style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f8; padding: 2em; text-align: center; }}
        .quiz-box {{ background: white; padding: 2em; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }}
        h2 {{ font-size: 1.5em; margin-bottom: 1em; }}
        form {{ margin-top: 1em; }}
        label {{ font-size: 1.1em; display: block; text-align: left; padding: 0.5em; }}
        input[type="radio"] {{ margin-right: 10px; }}
        button {{ margin-top: 1em; font-size: 1.1em; padding: 10px 20px; background: #007BFF; color: white; border: none; border-radius: 6px; cursor: pointer; }}
        button:hover {{ background-color: #0056b3; }}
        </style></head><body>
        <div class="quiz-box">
        <h2>Question {index + 1}</h2>
        <form action="/answer" method="post">
        <p style="font-size:1.2em;">{data['question']}</p>
        '''

        for choice in data['choices']:
            html += f'<label><input type="radio" name="choice" value="{choice}" required> {choice}</label>'

        html += '<button type="submit">Submit</button></form></div></body></html>'
        return html

    except Exception as e:
        logging.exception("Error in /question")
        return f"<pre>/question error:\n{e}</pre>", 500

@app.route('/answer', methods=['POST'])
def answer():
    try:
        index = session.get('index', 0)
        choice = request.form.get('choice')
        question = session['questions'][index]
        correct = question['answer']

        if choice == correct:
            session['score'] += 1
            session['difficulty'] = "hard" if session['difficulty'] == "medium" else "medium"
        else:
            session['difficulty'] = "easy" if session['difficulty'] == "medium" else "medium"

        session['index'] = index + 1
        return redirect(url_for('question'))

    except Exception as e:
        logging.exception("Error in /answer")
        return f"<pre>/answer error:\n{e}</pre>", 500

@app.route('/result')
def result():
    try:
        score = session.get('score', 0)
        total = session.get('num', 1)
        return f'''
        <html><head><style>
        body {{ font-family: 'Segoe UI', sans-serif; text-align: center; margin-top: 4em; }}
        h1 {{ font-size: 2em; }}
        </style></head>
        <body><h1>Your Score: {score} / {total}</h1>
        <a href="/">Start Over</a>
        </body></html>
        '''
    except Exception as e:
        logging.exception("Error in /result")
        return f"<pre>/result error:\n{e}</pre>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
