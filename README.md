# SAT Prep Quiz App

This Flask web application generates SAT practice quizzes for kids.
Users pick a topic (language or math), a grade level and how many questions
they want. Questions are generated with OpenAI's GPT model, and the app
displays them one at a time and scores the answers at the end.

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export your OpenAI API key (required for GPT generated questions):
   ```bash
   export OPENAI_API_KEY=your-key
   ```
   Optionally set a `FLASK_SECRET` to secure session data:
   ```bash
   export FLASK_SECRET=some-secret-key
   ```
3. Start the server:
   ```bash
   python main.py
   ```
4. Open `http://localhost:8080` in your browser to start a quiz. Questions
   will be presented one after another with a clean interface.

If no API key is provided, the app falls back to sample questions.

## Deploying to Cloud Run

Use the provided `deploy.sh` script to build and deploy the container to
Google Cloud Run.
