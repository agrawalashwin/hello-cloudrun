import os
import json
import logging
from flask import Flask, request, redirect, session, url_for, render_template
import openai

# Flask app setup
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
logging.basicConfig(level=logging.DEBUG)

# OpenAI client
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    # Initialize session for a new quiz
    session.clear()
    topic = request.form.get('topic', 'language')
    grade = request.form.get('grade', '3')
    num = int(request.form.get('num', 1))

    session.update({
        'topic': topic,
        'grade': grade,
        'num': num,
        'score': 0,
        'index': 0,
        'difficulty': 'medium',
        'questions': [],
        'difficulty_log': [],
        'time_log': []
    })

    # Pre-generate non-repeating questions
    questions = []
    seen = set()
    diff = session['difficulty']
    while len(questions) < num:
        prompt = (
            f"Generate 1 {diff} SAT-style multiple choice question for grade {grade} focusing on {topic}. "
            "Return ONLY the JSON object with keys 'question','choices','answer','concepts'."
        )
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.splitlines()[1:-1])
        try:
            q = json.loads(raw)
        except json.JSONDecodeError:
            continue
        text = q.get('question')
        if text and text not in seen:
            seen.add(text)
            questions.append(q)
            diff = {'easy':'medium','medium':'hard','hard':'medium'}[diff]
    session['questions'] = questions
    return redirect(url_for('question'))

@app.route('/question')
def question():
    i = session.get('index', 0)
    total = session.get('num', 1)
    if i >= total:
        return redirect(url_for('result'))

    q = session['questions'][i]
    progress = int((i + 1) / total * 100)
    return render_template(
        'question.html',
        question=q,
        index=i,
        total=total,
        progress=progress
    )

@app.route('/answer', methods=['POST'])
def answer():
    i = session.get('index', 0)
    time_taken = int(request.form.get('time', 0))
    session['time_log'].append(time_taken)

    choice = request.form.get('choice')
    correct = session['questions'][i]['answer']
    if choice == correct:
        session['score'] += 1
        diff = 'hard'
    else:
        diff = 'easy'
    session['difficulty_log'].append(diff)

    session['index'] = i + 1
    return redirect(url_for('question'))

@app.route('/result')
def result():
    score = session.get('score', 0)
    total = session.get('num', 1)
    levels = [ {'easy':1,'medium':2,'hard':3}.get(d,2) for d in session.get('difficulty_log', []) ]
    times = [round(t/1000,2) for t in session.get('time_log', [])]
    labels = list(range(1, total+1))
    return render_template(
        'result.html',
        score=score,
        total=total,
        levels=levels,
        times=times,
        labels=labels
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
