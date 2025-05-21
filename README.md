# SAT Prep Quiz App

This is a simple Flask web application that generates SAT practice quizzes for kids. Users can choose a topic (language or math), select the grade level, and specify how many questions they want. The app uses OpenAI's `gpt-4.1-mini-2025-04-14` model to create multiple choice questions, display them one at a time, and score the answers at the end.

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set the required environment variables (e.g. `OPENAI_API_KEY`).
3. Run the app:
   ```bash
   python main.py
   ```

## Deploying to Cloud Run

Cloud Run requires the service to listen on the port specified by the `PORT` environment variable. The application uses `port=int(os.environ.get('PORT', 8080))` in `app.run()` so it listens on the correct port by default.
