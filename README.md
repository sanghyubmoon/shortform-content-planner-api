# Short-form Content Planner API

Backend API for converting content plans to Google Docs with automatic permission management.

## Features

- Create Google Docs from content plan data
- Automatically grant editor permissions to specified users
- Integration with Bubble.io for frontend

## Architecture

1. **Bubble Frontend**: Generates content plans using OpenAI API
2. **This Backend**: Converts content to Google Docs and manages permissions

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

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-05-14T09:00:00",
  "google_services_initialized": true
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
  "content_plan": {
    "title": "Video Title",
    "topic": "AI Trends",
    "duration": 60,
    "key_message": "Main message",
    "scenes": [
      {
        "scene_number": 1,
        "duration": 10,
        "subtitle": "Opening text",
        "narration": "Voice over script",
        "visual_description": "Visual references"
      }
    ],
    "conclusion": "Closing message"
  },
  "user_email": "user@gmail.com"
}
```

Response:
```json
{
  "success": true,
  "document_id": "1234567890",
  "share_link": "https://docs.google.com/document/d/1234567890/edit"
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

### Deploy to Railway (Recommended)

1. Fork/Import this repository to your GitHub account
2. Go to [Railway](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your forked repository
5. Railway will automatically detect the app

#### Setting Environment Variables in Railway:

1. Click on your deployed service
2. Go to "Variables" tab
3. Add the following variables:

```bash
# Required API Key
BUBBLE_API_KEY=your-bubble-api-key-here

# Google Credentials - Option 1: Base64 encoded (Recommended)
GOOGLE_CREDENTIALS_JSON_BASE64=<your-base64-encoded-json>

# OR Option 2: Raw JSON
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

#### How to encode your Google credentials for Railway:

```bash
# On Mac/Linux:
base64 -i google-credentials.json | tr -d '\n'

# On Windows (PowerShell):
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("google-credentials.json"))
```

Then copy the output and paste it as the value for `GOOGLE_CREDENTIALS_JSON_BASE64`.

### Integration with Bubble

1. In Bubble, add API Connector plugin
2. Create new API with base URL of your deployed service
3. Add authentication header:
   ```
   X-API-Key: your_bubble_api_key
   ```
4. Add the endpoint:
   - Name: Create Google Doc
   - Method: POST
   - URL: /create-google-doc
5. Use in Bubble workflows after generating content with OpenAI

## Bubble Workflow Example

1. User inputs topic and email
2. Bubble calls OpenAI API to generate content plan
3. Bubble calls this backend API to create Google Doc
4. Backend returns link to shared document

## Troubleshooting

### Google Services Not Configured Error

If you get a "Google services not configured" error, check:

1. Your Google credentials are properly set in environment variables
2. The JSON format is valid
3. If using base64 encoding, ensure it's properly encoded without line breaks
4. Check service logs for any credential loading errors

### Health Check

You can verify your deployment by visiting:
```
https://your-deployed-url.com/health
```

This will show if Google services are properly initialized.

## Security Notes

⚠️ **NEVER commit `google-credentials.json` to Git**
- This file contains sensitive authentication data
- It's already in `.gitignore` to prevent accidental commits
- Use environment variables or secret management services in production

## License

MIT