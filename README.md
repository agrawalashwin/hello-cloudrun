# SAT Prep Quiz App

This is a simple Flask web application that generates SAT practice quizzes
for kids. Users choose a topic (language or math), select the grade level,
and specify how many questions they want. The app then uses OpenAI's
`gpt-4.1-mini-2025-04-14` model to create multiple choice questions and
scores the answers one point each. Questions are shown one at a time.

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export your OpenAI API key (optional but required for live questions):
   ```bash
   export OPENAI_API_KEY=your-key
   ```
3. Optionally set a secret key for sessions:
   ```bash
   export FLASK_SECRET=your-secret
   ```
4. Start the server:
   ```bash
   python main.py
   ```
5. Open `http://localhost:8080` in your browser to start a quiz.

If no API key is provided, the app falls back to sample questions.

## Deploying to Cloud Run

Use the provided `deploy.sh` script to build and deploy the container to
Google Cloud Run.
