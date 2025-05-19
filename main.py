import os
import json
from flask import Flask, request

import openai

app = Flask(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")

INDEX_HTML = '''
<h1>SAT Prep Quiz</h1>
<form action="/quiz" method="post">
  <label>Topic:
    <select name="topic">
      <option value="language">Language</option>
      <option value="math">Math</option>
    </select>
  </label><br>
  <label>Grade:
    <input type="number" name="grade" min="1" max="12" required>
  </label><br>
  <label>Number of questions:
    <input type="number" name="num" min="1" max="10" required>
  </label><br>
  <button type="submit">Start Quiz</button>
</form>
'''

@app.route('/', methods=['GET'])
def index():
    return INDEX_HTML

@app.route('/quiz', methods=['POST'])
def quiz():
    topic = request.form.get('topic', 'language')
    grade = request.form.get('grade', '3')
    num = int(request.form.get('num', 1))

    prompt = (
        "Generate a short SAT practice quiz for a grade {grade} student. "
        "Focus on {topic}. Provide {num} multiple choice questions. "
        "Return JSON formatted as a list of objects with fields 'question', "
        "'choices' (list of options), and 'answer' (the correct option)."
    ).format(grade=grade, topic=topic, num=num)

    if openai.api_key:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # GPT 4.1 mini placeholder
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            json_text = response.choices[0].message['content']
            questions = json.loads(json_text)
        except Exception:
            return "Failed to generate quiz", 500
    else:
        # Fallback quiz if no API key is provided
        questions = [
            {
                "question": "Sample question?",
                "choices": ["A", "B", "C", "D"],
                "answer": "A",
            }
            for _ in range(num)
        ]

    html = '<h1>Answer the Questions</h1>'
    html += '<form action="/score" method="post">'
    for idx, q in enumerate(questions):
        html += f'<p>{idx + 1}. {q["question"]}</p>'
        for choice in q["choices"]:
            html += (
                f'<label><input type="radio" name="q{idx}" ' \
                f'value="{choice}" required> {choice}</label><br>'
            )
        html += f'<input type="hidden" name="a{idx}" value="{q["answer"]}">'
    html += f'<input type="hidden" name="count" value="{len(questions)}">'
    html += '<button type="submit">Submit Answers</button></form>'
    return html

@app.route('/score', methods=['POST'])
def score():
    count = int(request.form.get('count', 0))
    score_value = 0
    for i in range(count):
        if request.form.get(f"q{i}") == request.form.get(f"a{i}"):
            score_value += 1
    return f'You scored {score_value} out of {count}.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
