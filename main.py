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


def generate_question(grade, topic, difficulty, used_concepts, used_questions):
    """Generate a unique question avoiding used concepts and questions."""
    prompt = (
        "Generate 1 {difficulty} SAT-style multiple choice question "
        "for a grade {grade} student focusing on {topic}. "
        "Avoid these concepts: {concepts}. Vary style and subtopics each time. "
        "Return JSON with keys 'question', 'choices' (list), 'answer', "
        "'explanation', and 'concepts' (list)."
    ).format(
        grade=grade,
        topic=topic,
        difficulty=difficulty,
        concepts=", ".join(used_concepts) or "none",
    )

    attempts = 0
    data = {}
    while attempts < 5:
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

        question_text = data.get("question", "")
        concepts = data.get("concepts", [])
        if (
            question_text not in used_questions
            and not set(concepts).intersection(used_concepts)
        ):
            break
        attempts += 1
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
        session['difficulty'] = "medium"
        session['questions'] = []
        session['difficulty_log'] = []
        session['used_concepts'] = []
        session['answer_log'] = []
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

        # Generate a new question if needed
        if index >= len(questions):
            used_concepts = session.get('used_concepts', [])
            used_questions = [q.get('question') for q in questions]
            data = generate_question(grade, topic, difficulty, used_concepts, used_questions)
            questions.append(data)
            session['questions'] = questions
            used_concepts.extend(data.get('concepts', []))
            session['used_concepts'] = used_concepts
        else:
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

        # Log the answer and explanation
        answers = session.get('answer_log', [])
        answers.append({
            'question': questions[index]['question'],
            'your_answer': choice,
            'correct_answer': correct,
            'explanation': questions[index].get('explanation', '')
        })
        session['answer_log'] = answers

        # Scoring + adaptive difficulty
        difficulty = session.get('difficulty', 'medium')
        if choice == correct:
            session['score'] += 1
            if difficulty == 'easy':
                difficulty = 'medium'
            elif difficulty == 'medium':
                difficulty = 'hard'
        else:
            if difficulty == 'hard':
                difficulty = 'medium'
            elif difficulty == 'medium':
                difficulty = 'easy'
        session['difficulty'] = difficulty

        # Track difficulty history
        log = session.get('difficulty_log', [])
        log.append(difficulty)
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
        answers = session.get('answer_log', [])

        # Fallback if no log is tracked
        if not difficulties:
            difficulties = ["medium"] * total

        # Convert difficulty to numeric scale
        level_map = {"easy": 1, "medium": 2, "hard": 3}
        level_labels = list(level_map.keys())
        level_data = [level_map.get(d, 2) for d in difficulties]

        rows = "".join(
            f"<tr><td>{a['question']}</td><td>{a['your_answer']}</td><td>{a['correct_answer']}</td><td>{a['explanation']}</td></tr>"
            for a in answers
        )

        return f'''
        <html>
        <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
          body {{ font-family: 'Segoe UI', sans-serif; text-align: center; margin-top: 4em; }}
          h1 {{ font-size: 2em; }}
          canvas {{ max-width: 600px; margin-top: 2em; }}
          table.summary {{ border-collapse: collapse; margin: 2em auto; width: 90%; }}
          table.summary th, table.summary td {{ border: 1px solid #ccc; padding: 0.5em; text-align: left; }}
          a {{ display: inline-block; margin-top: 2em; text-decoration: none; color: #007BFF; }}
        </style>
        </head>
        <body>
        <h1>Your Score: {score} / {total}</h1>

        <table class="summary">
          <tr><th>Question</th><th>Your Answer</th><th>Correct</th><th>Explanation</th></tr>
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
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
