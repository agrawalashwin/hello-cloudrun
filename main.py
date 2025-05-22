import os
import json
import logging
from flask import Flask, request, redirect, session, url_for
import openai

# Flask setup
app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
logging.basicConfig(level=logging.DEBUG)

# OpenAI SDK
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Quiz homepage template
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ari & Rishu's SAT Prep APP</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #f4f4f8; margin:0; padding:0; }
    nav { display: flex; align-items: center; padding: 1em; background: #007BFF; color: #fff; }
    nav img { height: 40px; margin-right: 0.5em; }
    nav h1 { font-size: 1.2em; margin: 0; }
    .quiz-box { background: white; padding: 2em; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: 2em auto; }
    h1 { font-size: 2em; margin-bottom: 0.5em; }
    label, select, input, button { font-size: 1.1em; margin-top: 10px; display: block; width: 100%; padding: 8px; }
    button { background-color: #007BFF; color: white; border: none; border-radius: 6px; cursor: pointer; }
    button:hover { background-color: #0056b3; }
  </style>
</head>
<body>
  <nav>
    <img src="/static/logo.png" alt="Logo">
    <h1>Ari & Rishu's SAT Prep APP</h1>
  </nav>
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
        session['difficulty_log'] = []
        session['time_log'] = []

        # Pre-generate all questions to avoid repeats
        questions = []
        seen = set()
        while len(questions) < num:
            prompt = (
                f"Generate 1 {session['difficulty']} SAT-style multiple choice question "
                f"for a grade {grade} student focusing on {topic}. "
                "Vary style and subtopics each time. "
                "Return JSON with keys 'question', 'choices' (list), 'answer', and 'concepts' (list)."
            )
            response = client.chat.completions.create(
                model="gpt-4.1-mini-2025-04-14",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
            )
            raw = response.choices[0].message.content.strip().lstrip('`')
            data = json.loads(raw)
            qtext = data.get('question')
            if qtext and qtext not in seen:
                seen.add(qtext)
                questions.append(data)
                # adjust difficulty randomly
                session['difficulty'] = {
                    'easy': 'medium',
                    'medium': 'hard',
                    'hard': 'medium'
                }[session['difficulty']]
        session['questions'] = questions

        return redirect(url_for('question'))
    except Exception as e:
        logging.exception("Error in /start")
        return f"<pre>/start error:\n{e}</pre>", 500

@app.route('/question')
def question():
    try:
        idx = session.get('index', 0)
        num = session.get('num', 1)
        if idx >= num:
            return redirect(url_for('result'))

        data = session['questions'][idx]
        progress_percent = int((idx + 1) / num * 100)

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Question {idx+1}</title>
  <script>
    let startTime;
    document.addEventListener('DOMContentLoaded', () => {{ startTime = Date.now(); }});
    function recordTime() {{
      const timeTaken = Date.now() - startTime;
      document.getElementById('time').value = timeTaken;
    }}
  </script>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f8; margin:0; padding:0; }}
    nav {{ display: flex; align-items: center; padding: 1em; background: #007BFF; color: #fff; position: sticky; top:0; z-index:100; }}
    nav img {{ height: 32px; margin-right: 0.5em; }}
    nav h1 {{ font-size: 1em; margin: 0; }}
    .timer {{ margin-left: auto; font-size: 1em; }}
    .quiz-box {{ background: white; padding: 2em; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: 3em auto 2em; }}
    .progress-bar {{ background: #ddd; border-radius: 5px; overflow: hidden; margin-bottom: 1em; }}
    .progress {{ width: {progress_percent}%; background: #28a745; height: 20px; }}
    h2 {{ font-size: 1.5em; margin-bottom: 1em; }}
    label {{ font-size: 1.1em; display: block; text-align: left; padding: 0.5em; }}
    input[type="radio"] {{ margin-right: 10px; }}
    button {{ margin-top: 1em; font-size: 1.1em; padding: 10px 20px; background: #007BFF; color: white; border: none; border-radius: 6px; cursor: pointer; }}
    button:hover {{ background-color: #0056b3; }}
    .concept-box {{ background: #e9ecef; padding: 0.5em; border-radius: 6px; margin: 1em 0; text-align: left; }}
  </style>
</head>
<body>
  <nav>
    <img src="/static/logo.png" alt="Logo">
    <h1>Ari & Rishu's SAT Prep APP</h1>
    <span class="timer">Time: <span id="timerDisplay">0</span>s</span>
  </nav>
  <div class="quiz-box">
    <div class="progress-bar"><div class="progress"></div></div>
    <p>Question {idx+1} of {num}</p>
    <h2>{data['question']}</h2>
    <div class="concept-box"><strong>Concepts:</strong> {', '.join(data.get('concepts', []))}</div>
    <form action="/answer" method="post" onsubmit="recordTime()">
      <input type="hidden" name="time" id="time" value="0">
'''  
        for c in data['choices']:
            html += f'<label><input type="radio" name="choice" value="{c}" required> {c}</label>'
        html += '''
      <button type="submit">Submit</button>
    </form>
  </div>
  <script>
    const display = document.getElementById('timerDisplay');
    setInterval(() => {{
      const sec = Math.floor((Date.now() - startTime)/1000);
      display.textContent = sec;
    }}, 500);
  </script>
</body>
</html>'''
        return html
    except Exception as e:
        logging.exception("Error in /question")
        return f"<pre>/question error:\n{e}</pre>", 500

@app.route('/answer', methods=['POST'])
def answer():
    try:
        idx = session.get('index', 0)
        num = session.get('num', 1)
        questions = session.get('questions', [])

        if idx >= len(questions):
            return redirect(url_for('question'))

        choice = request.form.get('choice')
        correct = questions[idx]['answer']
        time_taken = int(request.form.get('time', 0))

        # Track time
        tl = session.get('time_log', [])
        tl.append(time_taken)
        session['time_log'] = tl

        # Scoring + difficulty logic
        if choice == correct:
            session['score'] += 1
        # update difficulty for next question
        session['difficulty'] = 'hard' if choice == correct else 'easy'
        dl = session.get('difficulty_log', [])
        dl.append(session['difficulty'])
        session['difficulty_log'] = dl

        session['index'] = idx + 1
        return redirect(url_for('question'))
    except Exception as e:
        logging.exception("Error in /answer")
        return f"<pre>/answer error:\n{e}</pre>", 500

@app.route('/result')
def result():
    try:
        score = session.get('score', 0)
        total = session.get('num', 1)
        difficulties = session.get('difficulty_log', []) or ['medium']*total
        times = session.get('time_log', []) or [0]*total
        level_map = {"easy": 1, "medium": 2, "hard": 3}
        levels = [level_map.get(d,2) for d in difficulties]
        times_sec = [round(t/1000,2) for t in times]

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Results</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; text-align: center; margin:0; padding:0; }}
    nav {{ display:flex; align-items:center; padding:1em; background:#007BFF; color:#fff; }}
    nav img {{ height:32px; margin-right:0.5em; }}
    nav h1 {{ font-size:1em; margin:0; }}
    .content {{ padding:2em; }}
    canvas {{ max-width:600px; margin:2em auto; display:block; }}
    a {{ display:inline-block; margin-top:2em; text-decoration:none; color:#007BFF; }}
  </style>
</head>
<body>
  <nav>
    <img src="/static/logo.png" alt="Logo">
    <h1>Ari & Rishu's SAT Prep APP</h1>
  </nav>
  <div class="content">
    <h1>Your Score: {score} / {total}</h1>
    <canvas id="difficultyChart" width="600" height="300"></canvas>
    <canvas id="timeChart" width="600" height="300"></canvas>
    <a href="/">Start Over</a>
  </div>
  <script>
    const lvlCtx = document.getElementById('difficultyChart').getContext('2d');
    new Chart(lvlCtx, {{
      type: 'line',
      data: {{ labels: {list(range(1,len(levels)+1))}, datasets: [{{ label: 'Difficulty (1=Easy,3=Hard)', data: {levels}, tension:0.3 }}] }},
      options: {{ scales: {{ y: {{ min:1, max:3, ticks: {{ stepSize:1 }} }} }}}}
    }});

    const timeCtx = document.getElementById('timeChart').getContext('2d');
    new Chart(timeCtx, {{
      type: 'bar',
      data: {{ labels: {list(range(1,len(times_sec)+1))}, datasets: [{{ label: 'Time per Q (s)', data: {times_sec} }}] }},
      options: {{ scales: {{ y: {{ beginAtZero:true }} }} }}
    }});
  </script>
</body>
</html>'''
    except Exception as e:
        logging.exception("Error in /result")
        return f"<pre>/result error:\n{e}</pre>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
