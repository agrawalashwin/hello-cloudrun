import os, json, logging
from flask import Flask, request, redirect, session, url_for, render_template
import openai
import itertools

# Config
BLOCK_SIZE = 5

# App setup
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
logging.basicConfig(level=logging.DEBUG)
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Home
@app.route('/')
def index():
    return render_template('index.html')

# Initialize quiz
@app.route('/start', methods=['POST'])
def start():
    session.clear()
    session.update({
        'topic': request.form['topic'],
        'grade': request.form['grade'],
        'num': int(request.form['num']),
        'score': 0,
        'index': 0,
        'difficulty': 'medium',
        'questions': [],
        'difficulty_log': [],
        'time_log': [],
        'answers': [],
        'corrects': [],
        'explanations': []
    })
    generate_block()
    return redirect(url_for('question'))


def generate_block():
    topic   = session['topic']
    grade   = session['grade']
    total   = session['num']
    questions = session['questions']
    seen      = {q['question'] for q in questions}
    diff      = session['difficulty']

    to_gen = min(BLOCK_SIZE, total - len(questions))
    if to_gen <= 0:
        return

    # One API call to generate N questions
    prompt = (
        f"Generate {to_gen} SAT-style multiple-choice questions "
        f"at {diff} difficulty for a grade {grade} student on {topic}. "
        "Return ONLY a JSON array of objects, each with keys: "
        "'question','choices','answer','concepts','explanation'."
    )
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
    except json.JSONDecodeError:
        logging.error("Batch JSON decode failed:\n%s", raw)
        return

    # Dedupe & truncate exactly to to_gen
    new_qs = []
    for q in batch:
        if (isinstance(q, dict)
            and q.get('question') not in seen
            and isinstance(q.get('choices'), list)
            and len(q['choices']) == 4):
            seen.add(q['question'])
            new_qs.append(q)
            diff = {'easy':'medium','medium':'hard','hard':'medium'}[diff]
        if len(new_qs) >= to_gen:
            break

    questions.extend(new_qs)
    session['questions']  = questions
    session['difficulty'] = diff

# Show question

@app.route('/question')
def question():
    # Current index and total number of questions
    idx   = session.get('index', 0)
    total = session.get('num', 1)
    qs    = session.get('questions', [])

    # 1) If we've answered all requested questions, show results
    if idx >= total:
        return redirect(url_for('result'))

    # 2) If we’ve run out of pre-generated questions, fetch the next block
    if idx >= len(qs):
        generate_block()
        qs = session.get('questions', [])

    # 3) If still no questions (e.g. API error), bail to results
    if idx >= len(qs):
        return redirect(url_for('result'))

    # 4) Grab the current question and compute progress
    question = qs[idx]
    progress = int((idx + 1) / total * 100)

    # 5) Render via Jinja
    return render_template(
        'question.html',
        question=question,
        index=idx,
        total=total,
        progress=progress
    )

# Handle answer
@app.route('/answer', methods=['POST'])
def answer():
    i = session['index']
    t = int(request.form.get('time',0))
    session['time_log'].append(t)
    choice = request.form['choice']
    q = session['questions'][i]
    correct = q['answer']
    session['answers'].append(choice)
    session['corrects'].append(correct)
    session['explanations'].append(q.get('explanation',''))
    if choice == correct:
        session['score'] += 1
        diff = 'hard'
    else:
        diff = 'easy'
    session['difficulty_log'].append(diff)
    session['index'] = i+1
    return redirect(url_for('question'))

# Show results
@app.route('/result')
def result():
    score, total = session['score'], session['num']
    labels = list(range(1, total+1))
    levels = [ {'easy':1,'medium':2,'hard':3}.get(d,2) for d in session['difficulty_log'] ]
    times = [round(x/1000,2) for x in session['time_log']]
    answers = session['answers']; corrects=session['corrects']; exps=session['explanations']
    # Feedback: most missed concepts
    misses = {}
    for idx, ch in enumerate(answers):
        if ch != corrects[idx]:
            for c in session['questions'][idx]['concepts']:
                misses[c] = misses.get(c,0) + 1
    feedback = sorted(misses, key=misses.get, reverse=True)[:5]
    return render_template(
        'result.html', score=score, total=total,
        labels=labels, levels=levels, times=times,
        answers=answers, corrects=corrects, explanations=exps,
        feedback=feedback
    )

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))
