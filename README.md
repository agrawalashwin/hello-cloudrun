# SAT Prep Quiz App

This is a simple Flask web application that generates SAT practice quizzes for kids.  
Users can choose a topic (language or math), select the grade level, and specify how many questions they want.  
The app uses OpenAI’s `gpt-4.1-mini-2025-04-14` model to create multiple choice questions, displays them one at a time in a clean interface, and scores the answers at the end.

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
