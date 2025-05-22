import os
import json
import logging
from flask import Flask, request, redirect, session, url_for
import openai
 
# Flask setup
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret")
logging.basicConfig(level=logging.DEBUG)

# OpenAI SDK
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Quiz homepage template
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ari & Rishu's SAT Prep APP</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #f4f4f8; margin:0; padding:0; }
    nav { display: flex; align-items: center; justify-content: space-between; padding: 1em; background: #007BFF; color: #fff; position: sticky; top:0; z-index:100; }
    nav img { max-height: 40px; width: auto; }
    nav h1 { font-size: 1.2em; margin: 0 1em; flex-grow: 1; text-align: center; }
    .quiz-box { background: white; padding: 2em; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: 2em auto; }
    h1 { font-size: 2em; margin-bottom: 0.5em; }
    label, select, input, button { font-size: 1.1em; margin-top: 10px; display: block; width: 100%; padding: 8px; }
    button { background-color: #007BFF; color: white; border: none; border-radius: 6px; cursor: pointer; }
    button:hover { background-color: #0056b3; }
  </style>
</head>
<body>
  <nav>
    <img src="/static/logo.png" alt="Logo" onerror="this.style.display='none'">
    <h1>Ari & Rishu's SAT Prep APP</h1>
    <span></span>
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
"""

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

        # Pre-generate questions
        questions, seen, diff = [], set(), session['difficulty']
        while len(questions) < num:
            prompt = f"Generate 1 {diff} SAT-style multiple choice question for grade {grade} focusing on {topic}. Return ONLY the JSON object with keys 'question','choices','answer','concepts'."
            resp = client.chat.completions.create(
                model="gpt-4.1-mini-2025-04-14",
                messages=[{"role":"user","content":prompt}],
                temperature=0.9,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.splitlines()[1:-1])
            logging.debug("GPT: %s", raw)
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
    except Exception as e:
        logging.exception("/start error")
        return f"<pre>/start error:\n{e}</pre>",500

@app.route('/question')
def question():
    try:
        i, total = session['index'], session['num']
        if i >= total: return redirect(url_for('result'))
        q = session['questions'][i]
        pct = int((i+1)/total*100)
        html = f"""
<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Q{i+1}</title>
<style>body{{font-family:'Segoe UI',sans-serif;background:#f4f4f8;margin:0;padding:0}}nav{{display:flex;align-items:center;justify-content:space-between;padding:1em;background:#007BFF;color:#fff;position:sticky;top:0;}}nav img{{max-height:32px}}nav h1{{flex:1;text-align:center;font-size:1em;margin:0}}.box{{background:#fff;padding:2em;margin:3em auto 2em;border-radius:12px;max-width:600px;}}.prog{{background:#ddd;height:20px;border-radius:5px;overflow:hidden;margin-bottom:1em}}.fill{{width:{pct}%;background:#28a745;height:100%}}label{{display:block; padding:.5em;}}button{{margin-top:1em;padding:.5em 1em;border:none;border-radius:6px;background:#007BFF;color:#fff;font-size:1em;cursor:pointer}}</style>
<script>let st;document.addEventListener('DOMContentLoaded',()=>st=Date.now());function rec(){document.getElementById('t').value=Date.now()-st;}</script>
</head><body>
<nav><img src='/static/logo.png' onerror="this.style.display='none'"><h1>Ari & Rishu's SAT Prep APP</h1><span class='timer'>0s</span></nav>
<div class='box'><div class='prog'><div class='fill'></div></div><h2>Q{i+1} of {total}</h2><p>{q['question']}</p>
<form method='post' action='/answer' onsubmit='rec()'>
<input type='hidden' id='t' name='time' value='0'>
"""
        for c in q['choices']:
            html += f"<label><input type='radio' name='choice' value='{c}' required> {c}</label>"
        html += """
<button type='submit'>Submit</button></form></div>
<script>setInterval(()=>{let s=Math.floor((Date.now()-st)/1000);document.querySelector('.timer').textContent=s+'s';},500);</script>
</body></html>"""
        return html
    except Exception as e:
        logging.exception("/question error")
        return f"<pre>/question error:\n{e}</pre>",500

@app.route('/answer',methods=['POST'])
def answer():
    try:
        i = session['index']
        session['time_log'].append(int(request.form.get('time',0)))
        if request.form.get('choice') == session['questions'][i]['answer']:
            session['score'] += 1
        session['difficulty_log'].append('hard' if request.form.get('choice')==session['questions'][i]['answer'] else 'easy')
        session['index'] += 1
        return redirect(url_for('question'))
    except Exception as e:
        logging.exception("/answer error")
        return f"<pre>/answer error:\n{e}</pre>",500

@app.route('/result')
def result():
    try:
        score, total = session.get('score',0), session.get('num',1)
        levels = [ {'easy':1,'medium':2,'hard':3}.get(d,2) for d in session.get('difficulty_log',[]) ]
        times = [round(t/1000,2) for t in session.get('time_log',[])]
        labels = list(range(1,total+1))
        return f"""
<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Results</title><script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
<style>body{{font-family:'Segoe UI',sans-serif;text-align:center;margin:0;padding:0}}nav{{display:flex;align-items:center;justify-content:space-between;padding:1em;background:#007BFF;color:#fff}}nav img{{max-height:32px}}nav h1{{flex:1;text-align:center}}.cnt{{padding:2em}}canvas{{max-width:600px;margin:2em auto;display:block}}a{{margin-top:2em;display:inline-block;color:#007BFF;text-decoration:none}}</style>
</head><body>
<nav><img src='/static/logo.png' onerror="this.style.display='none'"><h1>Ari & Rishu's SAT Prep APP</h1><span></span></nav>
<div class='cnt'><h1>Your Score: {score} / {total}</h1>
<canvas id='c1'></canvas><canvas id='c2'></canvas><a href='/'>Start Over</a></div>
<script>
 const levels={json.dumps(levels)};
 const times={json.dumps(times)};
 const labels={json.dumps(labels)};
 new Chart(document.getElementById('c1').getContext('2d'),{{type:'line',data:{{labels:labels,datasets:[{{label:'Difficulty',data:levels,tension:0.3}}]}},options:{{scales:{{y:{{min:1,max:3,ticks:{{stepSize:1}}}}}}}}}});
 new Chart(document.getElementById('c2').getContext('2d'),{{type:'bar',data:{{labels:labels,datasets:[{{label:'Time per Q (s)',data:times}}]}},options:{{scales:{{y:{{beginAtZero:true}}}}}}}});
</script>
</body></html>"""
    except Exception as e:
        logging.exception("/result error")
        return f"<pre>/result error:\n{e}</pre>",500

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)))
