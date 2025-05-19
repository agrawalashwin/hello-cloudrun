import os
import json
import logging
from flask import Flask, request, redirect, session, url_for
import openai

# Flask setup
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
logging.basicConfig(level=logging.DEBUG)

# OpenAI SDK
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Quiz homepage
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
        session['topic'] = request.form.get('topic', 'language')
        session['grade'] = request.form.get('grade', '3')
        session['num'] = int(request.form.get('num', 1))
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
        questions = session.get('questions', [])

        if index >= num:
            return redirect(url_for('result'))

        # Only generate a new question if we haven't already
        if len(questions) <= index:
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

            if raw.startswith("```"):
                raw = raw.strip("` \n")
                if raw.startswith("json"):
                    raw = raw[4:].lstrip()

            data = json.loads(raw)
            session['questions'].append(data)
        else:
            data = questions[index]

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
        <h2>Question {index + 1} of {num}</h2>
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
        num = session.get('num', 1)
        questions = session.get('questions', [])

        # Guard: don't crash if somehow index > available questions
        if index >= len(questions):
            logging.warning("Answer submitted but question not yet generated.")
            return redirect(url_for('question'))

        choice = request.form.get('choice')
        correct = questions[index]['answer']

        # Scoring + difficulty logic
        if choice == correct:
            session['score'] += 1
            session['difficulty'] = "hard" if session['difficulty'] == "medium" else "medium"
        else:
            session['difficulty'] = "easy" if session['difficulty'] == "medium" else "medium"

        # Track difficulty history
        log = session.get('difficulty_log', [])
        log.append(session['difficulty'])
        session['difficulty_log'] = log

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
        difficulties = session.get('difficulty_log', [])

        # Fallback if no log is tracked
        if not difficulties:
            difficulties = ["medium"] * total

        # Convert difficulty to numeric scale
        level_map = {"easy": 1, "medium": 2, "hard": 3}
        level_labels = list(level_map.keys())
        level_data = [level_map.get(d, 2) for d in difficulties]

        return f'''
        <html>
        <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
          body {{ font-family: 'Segoe UI', sans-serif; text-align: center; margin-top: 4em; }}
          h1 {{ font-size: 2em; }}
          canvas {{ max-width: 600px; margin-top: 2em; }}
          a {{ display: inline-block; margin-top: 2em; text-decoration: none; color: #007BFF; }}
        </style>
        </head>
        <body>
        <h1>Your Score: {score} / {total}</h1>

        <canvas id="difficultyChart" width="600" height="300"></canvas>
        <script>
          const ctx = document.getElementById('difficultyChart').getContext('2d');
          const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
              labels: {list(range(1, len(level_data)+1))},
              datasets: [{{
                label: 'Question Difficulty (1=Easy, 3=Hard)',
                data: {level_data},
                borderColor: 'rgba(0, 123, 255, 1)',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                fill: true,
                tension: 0.3
              }}]
            }},
            options: {{
              scales: {{
                y: {{
                  min: 1,
                  max: 3,
                  ticks: {{
                    callback: function(value) {{
                      return ['','Easy','Medium','Hard'][value];
                    }},
                    stepSize: 1
                  }}
                }}
              }}
            }}
          }});
        </script>

        <a href="/">Start Over</a>
        </body>
        </html>
        '''
    except Exception as e:
        logging.exception("Error in /result")
        return f"<pre>/result error:\n{e}</pre>", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
