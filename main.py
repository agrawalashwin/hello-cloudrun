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


def generate_question(topic, grade, difficulty, used_questions, used_concepts):
    """Generate a single unique SAT-style question."""
    prompt = (
        f"Generate 1 {difficulty} SAT-style multiple choice question "
        f"for a grade {grade} student focusing on {topic}. "
        "Vary style and subtopics each time. "
        f"Avoid these concepts: {', '.join(used_concepts) if used_concepts else 'none'}. "
        "Return JSON with keys 'question', 'choices' (list), 'answer', "
        "'explanation', and 'concepts' (list of concepts tested)."
    )

    attempts = 0
    while True:
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.strip("` \n")
            if raw.startswith("json"):
                raw = raw[4:].lstrip()

        data = json.loads(raw)

        if data.get("question") not in used_questions and not any(
            c in used_concepts for c in data.get("concepts", [])
        ):
            used_questions.add(data.get("question"))
            used_concepts.update(data.get("concepts", []))
            return data

        attempts += 1
        if attempts >= 5:
            return data

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
        session['questions'] = []
        session['answer_log'] = []

        used_q = set()
        used_c = set()
        difficulties = []
        for i in range(session['num']):
            if i < session['num'] // 3:
                diff = "easy"
            elif i < 2 * session['num'] // 3:
                diff = "medium"
            else:
                diff = "hard"
            difficulties.append(diff)
            q = generate_question(session['topic'], session['grade'], diff, used_q, used_c)
            session['questions'].append(q)

        session['difficulty_log'] = difficulties
        return redirect(url_for('question'))
    except Exception as e:
        logging.exception("Error in /start")
        return f"<pre>/start error:\n{e}</pre>", 500


@app.route('/question')
def question():
    try:
        index = session.get('index', 0)
        num = session.get('num', 1)
        questions = session.get('questions', [])

        if index >= num:
            return redirect(url_for('result'))

        if index >= len(questions):
            logging.warning("Index out of range for questions list")
            return redirect(url_for('result'))
        data = questions[index]

        # Progress bar
        progress_percent = int((index + 1) / num * 100)
        progress_bar = f'''
        <div style="background: #ddd; border-radius: 5px; overflow: hidden; margin-bottom: 1em;">
          <div style="width: {progress_percent}%; background: #28a745; height: 20px;"></div>
        </div>
        <p>Question {index + 1} of {num}</p>
        '''

        html = f'''
        <html><head><style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f8; padding: 2em; text-align: center; }}
        .quiz-box {{ background: white; padding: 2em; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }}
        h2 {{ font-size: 1.5em; margin-bottom: 1em; }}
        form {{ margin-top: 1em; }}
        label {{ font-size: 1.1em; display: block; text-align: left; padding: 0.5em; }}
        input[type="radio"] {{ margin-right: 10px; }}
        .concept-box {{ background: #e9ecef; padding: 0.5em; border-radius: 6px; margin: 1em 0; text-align: left; }}
        button {{ margin-top: 1em; font-size: 1.1em; padding: 10px 20px; background: #007BFF; color: white; border: none; border-radius: 6px; cursor: pointer; }}
        button:hover {{ background-color: #0056b3; }}
        </style></head><body>
        <div class="quiz-box">
        <h2>{data['question']}</h2>
        {progress_bar}
        <div class="concept-box"><strong>Concepts:</strong> {', '.join(data.get('concepts', []))}</div>
        <form action="/answer" method="post">
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

        if choice == correct:
            session['score'] += 1

        log = session.get('answer_log', [])
        log.append({
            'question': questions[index]['question'],
            'your_answer': choice,
            'correct': correct,
            'explanation': questions[index].get('explanation', '')
        })
        session['answer_log'] = log

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
        answers = session.get('answer_log', [])

        # Fallback if no log is tracked
        if not difficulties:
            difficulties = ["medium"] * total

        # Convert difficulty to numeric scale
        level_map = {"easy": 1, "medium": 2, "hard": 3}
        level_labels = list(level_map.keys())
        level_data = [level_map.get(d, 2) for d in difficulties]

        rows = ""
        for i, entry in enumerate(answers, 1):
            rows += (
                f"<tr><td>{i}</td><td>{entry['your_answer']}</td>"
                f"<td>{entry['correct']}</td><td>{entry['explanation']}</td></tr>"
            )

        return f'''
        <html>
        <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
          body {{ font-family: 'Segoe UI', sans-serif; text-align: center; margin-top: 4em; }}
          h1 {{ font-size: 2em; }}
          canvas {{ max-width: 600px; margin-top: 2em; }}
          table, th, td {{ border: 1px solid #ccc; }}
          table {{ width: 100%; margin-top: 1em; }}
          th, td {{ padding: 6px; text-align: left; }}
          a {{ display: inline-block; margin-top: 2em; text-decoration: none; color: #007BFF; }}
        </style>
        </head>
        <body>
        <h1>Your Score: {score} / {total}</h1>

        <table style="margin:1em auto;border-collapse:collapse;max-width:600px;">
          <tr><th>#</th><th>Your Answer</th><th>Correct Answer</th><th>Explanation</th></tr>
          {rows}
        </table>

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
