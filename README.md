# SAT Prep Quiz App

This is a simple Flask web application that generates SAT practice quizzes for kids. Users can choose a topic (language or math), select the grade level, and specify how many questions they want. The app relies on OpenAI's `gpt-4.1-mini-2025-04-14` model to create unique multiple-choice questions and scores the answers at the end.


## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=<your-openai-api-key>
   ```
3. Start the application:
   ```bash
   python main.py
   ```
   The service will be available at `http://localhost:8080`.

## Build the Docker Image

Use Docker to package the application:
```bash
docker build -t hello-cloudrun .
```
To test locally:
```bash
docker run -p 8080:8080 -e OPENAI_API_KEY=$OPENAI_API_KEY hello-cloudrun
```

## Deploy to Cloud Run

Deployment is automated via the [GitHub Actions workflow](.github/workflows/deploy.yml). Configure the following repository secrets:

- `GCP_SA_KEY` – JSON service account key with permissions to deploy
- `GCP_PROJECT_ID` – your Google Cloud project ID
- `OPENAI_API_KEY` – your OpenAI API key

Pushing to the `main` branch triggers the workflow:
```bash
git push origin main
```
The workflow builds the image and deploys it to Cloud Run, then updates the service with your `OPENAI_API_KEY`.

To deploy manually, you can run:
```bash
bash deploy.sh
```

