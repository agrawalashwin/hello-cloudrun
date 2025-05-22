import os, json, logging
from flask import (
    Flask, request, redirect, session, url_for,
    render_template, after_this_request
)
import openai

# ─── App setup ───────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR    = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static",
)
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
logging.basicConfig(level=logging.DEBUG)
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

BLOCK_SIZE = 5

@app.after_request
def set_cache_headers(response):
    if request.path.startswith("/static/"):
        response.cache_control.max_age = 31536000
    return response

def generate_block(count=None):
    topic    = session["topic"]
    subtopic = session.get("subtopic", "").strip()
    grade    = session["grade"]
    total    = session["num"]
    qs       = session["questions"]
    seen     = {q["question"] for q in qs}
    diff     = session["difficulty"]

    to_gen = count if count is not None else BLOCK_SIZE
    to_gen = min(to_gen, total - len(qs))
    if to_gen <= 0:
        return

    # Build the prompt; include subtopic if provided
    prompt = (
        f"Generate {to_gen} SAT-style multiple-choice questions "
        f"at {diff} difficulty for a grade {grade} student on {topic}"
    )
    if subtopic:
        prompt += f" focusing specifically on {subtopic}"
    prompt += ". Return ONLY a JSON array of objects, each with keys: " \
              "'question','choices','answer','concepts','explanation'."

    resp = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[{"role":"user","content":prompt}],
        temperature=0.9,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:-1])

    try:
        batch = json.loads(raw)
    except Exception:
        logging.error("Failed JSON parse:\n%s", raw)
        return

    new_qs = []
    for q in batch:
        if (
            isinstance(q, dict)
            and q.get("question") not in seen
            and isinstance(q.get("choices"), list)
            and len(q["choices"]) == 4
        ):
            seen.add(q["question"])
            new_qs.append(q)
            diff = {"easy":"medium","medium":"hard","hard":"medium"}[diff]
        if len(new_qs) >= to_gen:
            break

    qs.extend(new_qs)
    session["questions"]  = qs
    session["difficulty"] = diff

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    session.clear()
    session.update({
        "topic":       request.form["topic"],
        "subtopic":    request.form.get("subtopic","").strip(),
        "grade":       request.form["grade"],
        "num":         int(request.form["num"]),
        "score":       0,
        "index":       0,
        "difficulty":  "medium",
        "questions":      [],
        "difficulty_log": [],
        "time_log":       [],
        "answers":        [],
        "corrects":       [],
        "explanations":   [],
    })
    # Pre-generate entire quiz
    generate_block(count=session["num"])
    return redirect(url_for('question'))

@app.route('/question')
def question():
    idx   = session["index"]
    total = session["num"]
    qs    = session["questions"]
    if idx >= total:
        return redirect(url_for('result'))
    if idx >= len(qs):
        generate_block()
    return render_template(
        'question.html',
        question=qs[idx],
        index=idx,
        total=total,
        progress=int((idx+1)/total*100)
    )

@app.route('/answer', methods=['POST'])
def answer():
    i       = session["index"]
    elapsed = int(request.form.get("time",0))
    session["time_log"].append(elapsed)

    choice  = request.form["choice"]
    q       = session["questions"][i]
    correct = q["answer"]

    session["answers"].append(choice)
    session["corrects"].append(correct)
    session["explanations"].append(q["explanation"])

    prev = session["difficulty"]
    if choice == correct:
        session["score"] += 1
        diff = {"easy":"medium","medium":"hard","hard":"medium"}[prev]
    else:
        diff = {"easy":"medium","medium":"easy","hard":"medium"}[prev]

    session["difficulty"]     = diff
    session["difficulty_log"].append(diff)
    session["index"] = i + 1
    return redirect(url_for('question'))

@app.route('/result')
def result():
    score, total = session["score"], session["num"]
    labels  = list(range(1, total+1))
    levels  = [ {"easy":1,"medium":2,"hard":3}.get(d,2)
                for d in session["difficulty_log"] ]
    times   = [round(x/1000,2) for x in session["time_log"]]
    answers = session["answers"]
    corrects= session["corrects"]
    exps    = session["explanations"]

    # Feedback
    misses = {}
    for idx, ans in enumerate(answers):
        if ans != corrects[idx]:
            for c in session["questions"][idx]["concepts"]:
                misses[c] = misses.get(c,0) + 1
    feedback = sorted(misses, key=misses.get, reverse=True)[:5]

    return render_template(
        'result.html',
        score=score, total=total,
        labels=labels, levels=levels, times=times,
        answers=answers, corrects=corrects,
        explanations=exps, feedback=feedback
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",8080)))
