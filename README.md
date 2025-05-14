# Short-form Content Planner API

AI-powered backend API for generating short-form content plans with Google Docs integration.

## Features

- Generate content plans using OpenAI GPT-4
- Create Google Docs automatically
- Grant editor permissions to specified users
- Integration with Bubble.io for frontend

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/sanghyubmoon/shortform-content-planner-api.git
cd shortform-content-planner-api
```

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your API keys in `.env`:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `BUBBLE_API_KEY`: API key for authenticating Bubble requests

3. Set up Google Cloud credentials:
   - Create a service account in Google Cloud Console
   - Download the JSON credentials file
   - Save it as `google-credentials.json` in the project root
   - Enable Google Docs API and Google Drive API in your project

### 4. Run locally

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Generate Content Plan

```
POST /generate-plan
Headers:
  X-API-Key: your_bubble_api_key
  Content-Type: application/json

Body:
{
  "topic": "AI trends in 2025",
  "duration": 60
}
```

### Create Google Doc

```
POST /create-google-doc
Headers:
  X-API-Key: your_bubble_api_key
  Content-Type: application/json

Body:
{
  "content_plan": { ... },
  "user_email": "user@gmail.com"
}
```

## Google Cloud Setup

### Required APIs
Enable these APIs in your Google Cloud project:
- Google Docs API
- Google Drive API

### Service Account Setup
1. Go to Google Cloud Console
2. Navigate to IAM & Admin > Service Accounts
3. Create new service account with these permissions:
   - Google Docs Editor
   - Google Drive File Editor
4. Create and download JSON key
5. Save as `google-credentials.json` in project root

## Deployment

### Option 1: Deploy to Render.com

1. Create a new Web Service on Render
2. Connect this GitHub repository
3. Add environment variables:
   - `OPENAI_API_KEY`
   - `BUBBLE_API_KEY`
4. Add Secret File:
   - Filename: `google-credentials.json`
   - Content: Your service account JSON
5. Deploy

### Option 2: Deploy to Google Cloud Run

```bash
# Store credentials in Secret Manager
gcloud secrets create google-creds --data-file=google-credentials.json

# Build and push container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/content-planner-api

# Deploy to Cloud Run with secrets
gcloud run deploy content-planner-api \
  --image gcr.io/YOUR_PROJECT_ID/content-planner-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --update-secrets=/app/google-credentials.json=google-creds:latest \
  --set-env-vars="OPENAI_API_KEY=your_key,BUBBLE_API_KEY=your_key"
```

### Option 3: Deploy to Railway

1. Connect your GitHub repository to Railway
2. Add environment variables:
   - `OPENAI_API_KEY`
   - `BUBBLE_API_KEY`
3. Upload `google-credentials.json` via Railway CLI:
   ```bash
   railway link
   railway variables set GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
   railway up google-credentials.json
   ```
4. Deploy

## Integration with Bubble

1. In Bubble, add API Connector plugin
2. Create new API with base URL of your deployed service
3. Add authentication header:
   ```
   X-API-Key: your_bubble_api_key
   ```
4. Add the two endpoints with appropriate parameters
5. Use in Bubble workflows

## Security Notes

⚠️ **NEVER commit `google-credentials.json` to Git**
- This file contains sensitive authentication data
- It's already in `.gitignore` to prevent accidental commits
- Use environment variables or secret management services in production

## License

MIT