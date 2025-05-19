# SAT Prep Quiz App

This Flask web application generates SAT practice quizzes for kids. Users
choose a topic (language or math), select the grade level and how many
questions they want. The app uses OpenAI's `gpt-4.1-mini-2025-04-14` model to
create multiple choice questions, shows them one at a time in large text and scores the
answers at the end.

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export your OpenAI API key (optional but required for live questions):
   ```bash
   export OPENAI_API_KEY=your-key
   ```
   Optionally set a `FLASK_SECRET` to secure session data:
   ```bash
   export FLASK_SECRET=some-secret
   ```
3. Start the server:
   ```bash
   python main.py
   ```
4. Open `http://localhost:8080` in your browser to start a quiz. Questions
   appear sequentially with a clean interface.

If no API key is provided, the app falls back to sample questions.

## Deploying to Cloud Run

Use the provided `deploy.sh` script to build and deploy the container to
Google Cloud Run.
