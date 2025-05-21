import os
import json
import logging

from flask import (
    Flask, request, redirect, session,
    url_for, render_template_string
)
from flask_session import Session
import openai

# ─── App & Session Setup ───────────────────────────────────────────────────────
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET", "devsecret"),
    SESSION_TYPE="filesystem",
)
Session(app)

logging.basicConfig(level=logging.DEBUG)

openai.api_key = os.environ.get("OPENAI_API_KEY")


# ─── Shared Templates & Styles ─────────────────────────────────────────────────
GLOBAL_STYLES = """
body { font-family: 'Segoe UI', sans-serif; background: #f4f4f8; margin:0; padding-top:60px; text-align:center; }
.quiz-box { background:white; padding:2em; border-radius:12px; box-shadow:0 0 10px rgba(0,0,0,0.1); max-width:600px; margin:auto; }
.navbar { position:fixed; top:0; left:0; right:0; display:flex; align-items:center; justify-content:center;
           background:#007BFF; color:#fff; padding:0.5em 1em; box-sizing:border-box; }
.navbar img { width:40px; height:40px; margin-right:10px; }
.navbar .brand { display:flex; align-items:center; font-weight:bold; font-size:1.2em; }
@media (max-width:600px) {
  .navbar { flex-direction:column; }
  body { padding-top:80px; }
}
"""

NAV_BAR = """
<nav class="navbar">
  <div class="brand">
    <img src="https://via.placeholder.com/40" alt="Logo">
    <span>Ari and Rishu SAT Prep App</span>
  </div>
</nav>
"""

INDEX_HTML = f"""
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>{GLOBAL_STYLES}
    label, select, input, button {{ font-size:1.1em; margin-top:10px; display:block; width:100%; padding:8px; }}
    button {{ background:#007BFF; color:#fff; border:none; border-radius:6px; cursor:pointer; }}
    button:hover {{ background:#0056b3; }}
  </style>
</head>
<body>
  {NAV_BAR}
  <div class="quiz-box">
    <h1>Welcome to Ari and Rishu SAT Prep App</h1>
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
"""


# ─── OpenAI Question Generator ─────────────────────────────────────────────────
def generate_question(grade, topic, difficulty, used_concepts, used_questions):
    prompt = (
        f"Generate 1 {difficulty} SAT-style multiple choice question "
        f"for a grade {grade} student focusing on {topic}. "
        f"Avoid these concepts: {', '.join(used_concepts) or 'none'}. "
        "Return JSON with keys 'question', 'choices' (list), "
        "'answer', 'explanation', and 'concepts' (list)."
    )

    for attempt in range(5):
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4.1-mini-2025-04-14",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
            )
            raw = resp.choices[0].message.content.strip()
            # strip ```json fences if present
            if raw.startswith("```"):
                raw = raw.strip("` \n")
                if raw.startswith("json"):
                    raw = raw[4:].lstrip()
            data = json.loads(raw)
        except Exception:
            logging.exception("OpenAI parsing failed, retrying...")
            continue

        txt = data.get("question", "")
        concepts = data.get("concepts", [])
        if txt not in used_questions and not set(concepts).intersection(used_concepts):
            return data

    # fallback if no unique question
    return {
        "question": "Something went wrong generating a question.",
        "choices": ["--"],
        "answer": "--",
        "explanation": "",
        "concepts": []
    }


# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return INDEX_HTML


@app.route("/start", methods=["POST"])
def start():
    try:
        session.clear()
        session.update({
            "topic": request.form["topic"],
            "grade": request.form["grade"],
            "num": int(request.form["num"]),
            "score": 0,
            "index": 0,
            "questions": [],
            "used_concepts": [],
            "difficulty_log": [],
            "answer_log": [],
            "difficulty": "medium",
        })
        return redirect(url_for("question"))
    except Exception:
        logging.exception("Error in /start")
        return "<pre>/start error</pre>", 500


@app.route("/question", methods=["GET"])
def question():
    try:
        idx = session["index"]
        total = session["num"]
        if idx >= total:
            return redirect(url_for("result"))

        questions = session["questions"]
        used_concepts = session["used_concepts"]
        # generate new if needed
        if idx >= len(questions):
            prev_qs = [q["question"] for q in questions]
            q = generate_question(
                session["grade"], session["topic"],
                session["difficulty"], used_concepts, prev_qs
            )
            questions.append(q)
            used_concepts += q.get("concepts", [])
            session["questions"] = questions
            session["used_concepts"] = used_concepts
        else:
            q = questions[idx]

        progress = int((idx + 1) / total * 100)
        tmpl = f"""
        <!doctype html>
        <html>
        <head>
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <style>{GLOBAL_STYLES}
            h2 {{ font-size:1.5em; margin-bottom:1em; }}
            .concept-box {{ background:#e9ecef; padding:.5em; border-radius:6px; }}
            label {{ display:block; text-align:left; margin: .5em 0; }}
            button {{ margin-top:1em; width:100%; padding:10px; font-size:1.1em; background:#007BFF; color:#fff; border:none; border-radius:6px; cursor:pointer; }}
            button:hover {{ background:#0056b3; }}
            .progress {{ background:#ddd; border-radius:5px; overflow:hidden; }}
            .progress-bar {{ width:{progress}%; background:#28a745; height:20px; }}
          </style>
        </head>
        <body>
          {NAV_BAR}
          <div class="quiz-box">
            <h2>{q['question']}</h2>
            <div class="progress"><div class="progress-bar"></div></div>
            <p>Question {idx+1} of {total}</p>
            <div class="concept-box">
              <strong>Concepts:</strong> {', '.join(q.get('concepts', []))}
            </div>
            <form action="/answer" method="post">
              {"".join(
                  f"<label><input type='radio' name='choice' value='{c}' required> {c}</label>"
                  for c in q['choices']
              )}
              <button type="submit">Submit</button>
            </form>
          </div>
        </body>
        </html>
        """
        return tmpl

    except Exception:
        logging.exception("Error in /question")
        return "<pre>/question error</pre>", 500


@app.route("/answer", methods=["POST"])
def answer():
    try:
        idx = session["index"]
        questions = session["questions"]
        choice = request.form["choice"]
        correct = questions[idx]["answer"]

        # log answer
        session["answer_log"].append({
            "question": questions[idx]["question"],
            "your_answer": choice,
            "correct_answer": correct,
            "explanation": questions[idx].get("explanation", "")
        })

        # scoring + adaptive difficulty
        diff = session["difficulty"]
        if choice == correct:
            session["score"] += 1
            diff = {"easy":"medium","medium":"hard"}.get(diff, diff)
        else:
            diff = {"hard":"medium","medium":"easy"}.get(diff, diff)
        session["difficulty"] = diff
        session["difficulty_log"].append(diff)

        session["index"] = idx + 1
        return redirect(url_for("question"))

    except Exception:
        logging.exception("Error in /answer")
        return "<pre>/answer error</pre>", 500


@app.route("/result", methods=["GET"])
def result():
    try:
        score = session["score"]
        total = session["num"]
        diffs = session["difficulty_log"] or ["medium"] * total
        level_map = {"easy":1,"medium":2,"hard":3}
        levels = [level_map.get(d,2) for d in diffs]
        rows = "".join(
            f"<tr><td>{a['question']}</td>"
            f"<td>{a['your_answer']}</td>"
            f"<td>{a['correct_answer']}</td>"
            f"<td>{a['explanation']}</td></tr>"
            for a in session["answer_log"]
        )

        # render final page
        return render_template_string(f"""
        <!doctype html>
        <html>
        <head>
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
          <style>{GLOBAL_STYLES}
            h1 {{ font-size:2em; }}
            canvas {{ max-width:600px; margin:2em auto; display:block; }}
            table {{ border-collapse:collapse; margin:2em auto; width:90%; }}
            th,td {{ border:1px solid #ccc; padding:.5em; text-align:left; }}
            a {{ display:inline-block; margin:2em; color:#007BFF; text-decoration:none; }}
          </style>
        </head>
        <body>
          {NAV_BAR}
          <h1>Your Score: {{score}} / {{total}}</h1>
          <canvas id="difficultyChart"></canvas>
          <script>
            new Chart(
              document.getElementById('difficultyChart'),
              {{
                type:'line',
                data:{{ labels:{list(range(1,len(levels)+1))}, datasets:[{{ 
                  label:'Difficulty (1=Easy,3=Hard)',
                  data:{levels},
                  fill:true, tension:0.3
                }}]}},
                options:{{ scales:{{ y:{{ min:1,max:3, ticks:{{ stepSize:1, callback: v=>['','Easy','Medium','Hard'][v] }}}}}}}}
              }}
            );
          </script>
          <table>
            <tr><th>Question</th><th>Your Answer</th><th>Correct</th><th>Explanation</th></tr>
            {rows}
          </table>
          <a href="/">Start Over</a>
        </body>
        </html>
        """, score=score, total=total)

    except Exception:
        logging.exception("Error in /result")
        return "<pre>/result error</pre>", 500


# ─── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
