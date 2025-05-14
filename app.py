from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
from datetime import datetime
import logging
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for Bubble integration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Keys from environment variables
openai.api_key = os.environ.get('OPENAI_API_KEY')
GOOGLE_CREDENTIALS_FILE = 'google-credentials.json'

class ContentPlannerAPI:
    def __init__(self):
        self.openai_client = None
        self.docs_service = None
        self.drive_service = None
        
        try:
            # Initialize OpenAI if key exists
            if openai.api_key:
                self.openai_client = openai.OpenAI(api_key=openai.api_key)
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OpenAI API key not found")
            
            # Initialize Google services
            # Method 1: From file
            if os.path.exists(GOOGLE_CREDENTIALS_FILE):
                self.google_creds = service_account.Credentials.from_service_account_file(
                    GOOGLE_CREDENTIALS_FILE,
                    scopes=['https://www.googleapis.com/auth/documents',
                           'https://www.googleapis.com/auth/drive']
                )
                logger.info("Google credentials loaded from file")
            
            # Method 2: From environment variable (JSON)
            elif os.environ.get('GOOGLE_CREDENTIALS_JSON'):
                creds_json = json.loads(os.environ.get('GOOGLE_CREDENTIALS_JSON'))
                self.google_creds = service_account.Credentials.from_service_account_info(
                    creds_json,
                    scopes=['https://www.googleapis.com/auth/documents',
                           'https://www.googleapis.com/auth/drive']
                )
                logger.info("Google credentials loaded from JSON env var")
            
            # Method 3: From environment variable (Base64)
            elif os.environ.get('GOOGLE_CREDENTIALS_JSON_BASE64'):
                import base64
                creds_base64 = os.environ.get('GOOGLE_CREDENTIALS_JSON_BASE64')
                creds_json = json.loads(base64.b64decode(creds_base64).decode('utf-8'))
                self.google_creds = service_account.Credentials.from_service_account_info(
                    creds_json,
                    scopes=['https://www.googleapis.com/auth/documents',
                           'https://www.googleapis.com/auth/drive']
                )
                logger.info("Google credentials loaded from Base64 env var")
            else:
                logger.warning("No Google credentials found")
                return
            
            # Build services
            self.docs_service = build('docs', 'v1', credentials=self.google_creds)
            self.drive_service = build('drive', 'v3', credentials=self.google_creds)
            logger.info("Google services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {str(e)}")
            logger.error(traceback.format_exc())
    
    def generate_content_plan(self, topic, duration):
        """Generate content plan using AI"""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
            
        prompt = f"""
        Create a content plan for a short-form video.
        
        Topic: {topic}
        Duration: {duration} seconds
        
        Please respond in JSON format with the following structure:
        {{
            "title": "Video title",
            "topic": "{topic}",
            "duration": {duration},
            "key_message": "Main message of the video",
            "scenes": [
                {{
                    "scene_number": 1,
                    "duration": 10,
                    "subtitle": "Text for subtitle",
                    "narration": "Narration script",
                    "visual_description": "Description of visuals or reference images"
                }}
            ],
            "conclusion": "Closing message"
        }}
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)

# Initialize the planner
planner = ContentPlannerAPI()

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        "status": "online",
        "service": "Content Planner API",
        "endpoints": ["/health", "/generate-plan", "/create-google-doc"]
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": bool(planner.openai_client),
            "google_docs": bool(planner.docs_service),
            "google_drive": bool(planner.drive_service)
        }
    })

@app.route('/generate-plan', methods=['POST'])
def generate_plan():
    """Generate content plan endpoint"""
    try:
        logger.info("Received generate-plan request")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Data: {request.json}")
        
        # Validate API key
        api_key = request.headers.get('X-API-Key')
        expected_key = os.environ.get('BUBBLE_API_KEY')
        
        if not expected_key:
            logger.error("BUBBLE_API_KEY not set in environment")
            return jsonify({'success': False, 'error': 'Server configuration error'}), 500
        
        if api_key != expected_key:
            logger.warning(f"Invalid API key: received '{api_key}', expected '{expected_key}'")
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        # Check if planner is initialized
        if not planner.openai_client:
            return jsonify({
                'success': False,
                'error': 'OpenAI service not initialized'
            }), 503
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
            
        topic = data.get('topic')
        duration = data.get('duration', 60)
        
        if not topic:
            return jsonify({'success': False, 'error': 'Topic is required'}), 400
        
        # Generate content plan
        content_plan = planner.generate_content_plan(topic, duration)
        
        return jsonify({
            'success': True,
            'content_plan': content_plan
        })
    
    except Exception as e:
        logger.error(f"Error in generate_plan: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/create-google-doc', methods=['POST'])
def create_google_doc():
    """Create Google Doc and grant permissions"""
    try:
        logger.info("Received create-google-doc request")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Data: {request.json}")
        
        # Validate API key
        api_key = request.headers.get('X-API-Key')
        expected_key = os.environ.get('BUBBLE_API_KEY')
        
        if not expected_key:
            logger.error("BUBBLE_API_KEY not set in environment")
            return jsonify({'success': False, 'error': 'Server configuration error'}), 500
        
        if api_key != expected_key:
            logger.warning(f"Invalid API key: received '{api_key}', expected '{expected_key}'")
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        # Check if Google services are initialized
        if not planner.docs_service or not planner.drive_service:
            return jsonify({
                'success': False,
                'error': 'Google services not initialized'
            }), 503
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
            
        content_plan = data.get('content_plan')
        user_email = data.get('user_email')
        
        if not content_plan:
            return jsonify({'success': False, 'error': 'content_plan is required'}), 400
            
        if not user_email:
            return jsonify({'success': False, 'error': 'user_email is required'}), 400
        
        # Parse content_plan if it's a string
        if isinstance(content_plan, str):
            try:
                content_plan = json.loads(content_plan)
            except:
                logger.warning("Could not parse content_plan as JSON")
        
        # Create Google Doc
        document = planner.docs_service.documents().create(
            body={'title': f"Short-form Content Plan: {content_plan.get('title', 'Untitled')}"}  
        ).execute()
        
        document_id = document['documentId']
        logger.info(f"Created document with ID: {document_id}")
        
        # Add content to document
        requests = format_content_for_docs(content_plan)
        planner.docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        
        # Grant editor permission
        permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': user_email
        }
        
        planner.drive_service.permissions().create(
            fileId=document_id,
            body=permission,
            sendNotificationEmail=True
        ).execute()
        
        logger.info(f"Granted permission to: {user_email}")
        
        # Generate share link
        share_link = f"https://docs.google.com/document/d/{document_id}/edit"
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'share_link': share_link
        })
    
    except Exception as e:
        logger.error(f"Error in create_google_doc: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def format_content_for_docs(content_plan):
    """Format content for Google Docs"""
    requests = []
    current_index = 1
    
    # Add title
    title_text = f"{content_plan.get('title', 'Untitled')}\n\n"
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': title_text
        }
    })
    current_index += len(title_text)
    
    # Add metadata
    metadata_text = f"Topic: {content_plan.get('topic', '')}\nDuration: {content_plan.get('duration', 60)} seconds\nKey Message: {content_plan.get('key_message', '')}\n\n"
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': metadata_text
        }
    })
    current_index += len(metadata_text)
    
    # Add scenes
    scenes_text = "Scene Breakdown:\n\n"
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': scenes_text
        }
    })
    current_index += len(scenes_text)
    
    for scene in content_plan.get('scenes', []):
        scene_text = f"""Scene {scene.get('scene_number', 0)}: {scene.get('duration', 0)} seconds
Subtitle: {scene.get('subtitle', '')}
Narration: {scene.get('narration', '')}
Visual Reference: {scene.get('visual_description', '')}

"""
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': scene_text
            }
        })
        current_index += len(scene_text)
    
    # Add conclusion
    conclusion_text = f"\nConclusion: {content_plan.get('conclusion', '')}"
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': conclusion_text
        }
    })
    
    return requests

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)