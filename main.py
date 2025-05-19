import os
import json
import logging
import traceback
from flask import Flask, request

import openai

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")


def parse_json_response(text: str):
    """Attempt to parse JSON from the API response."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None

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
            questions = parse_json_response(json_text)
            if not questions:
                raise ValueError("Invalid JSON from API")
        except Exception as exc:
            logger.error("OpenAI request failed: %s", exc)
            logger.debug("Response text: %s", locals().get('json_text'))
            logger.debug(traceback.format_exc())
            return "Failed to generate quiz", 500
    else:
        # Fallback quiz if no API key is provided
        logger.info("Using fallback questions. OPENAI_API_KEY not set.")
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
