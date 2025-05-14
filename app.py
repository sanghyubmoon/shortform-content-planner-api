from flask import Flask, request, jsonify
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
import base64
from datetime import datetime
import logging
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for Bubble integration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentPlannerAPI:
    def __init__(self):
        self.docs_service = None
        self.drive_service = None
        
        try:
            # Method 1: Try environment variable with base64 encoded JSON
            google_creds_base64 = os.environ.get('GOOGLE_CREDENTIALS_JSON_BASE64')
            if google_creds_base64:
                try:
                    # Decode base64 and parse JSON
                    google_creds_json = base64.b64decode(google_creds_base64).decode('utf-8')
                    google_creds_dict = json.loads(google_creds_json)
                    
                    # Create credentials from dictionary
                    self.google_creds = service_account.Credentials.from_service_account_info(
                        google_creds_dict,
                        scopes=['https://www.googleapis.com/auth/documents',
                               'https://www.googleapis.com/auth/drive']
                    )
                    self.docs_service = build('docs', 'v1', credentials=self.google_creds)
                    self.drive_service = build('drive', 'v3', credentials=self.google_creds)
                    logger.info("Successfully initialized Google services from base64 environment variable")
                except Exception as e:
                    logger.error(f"Error loading Google credentials from base64: {e}")
                    logger.error(traceback.format_exc())
            
            # Method 2: Try raw JSON from environment variable
            elif os.environ.get('GOOGLE_CREDENTIALS_JSON'):
                try:
                    google_creds_dict = json.loads(os.environ.get('GOOGLE_CREDENTIALS_JSON'))
                    self.google_creds = service_account.Credentials.from_service_account_info(
                        google_creds_dict,
                        scopes=['https://www.googleapis.com/auth/documents',
                               'https://www.googleapis.com/auth/drive']
                    )
                    self.docs_service = build('docs', 'v1', credentials=self.google_creds)
                    self.drive_service = build('drive', 'v3', credentials=self.google_creds)
                    logger.info("Successfully initialized Google services from JSON environment variable")
                except Exception as e:
                    logger.error(f"Error loading Google credentials from JSON env: {e}")
                    logger.error(traceback.format_exc())
                    
            # Method 3: Try file if it exists
            elif os.path.exists('google-credentials.json'):
                try:
                    self.google_creds = service_account.Credentials.from_service_account_file(
                        'google-credentials.json',
                        scopes=['https://www.googleapis.com/auth/documents',
                               'https://www.googleapis.com/auth/drive']
                    )
                    self.docs_service = build('docs', 'v1', credentials=self.google_creds)
                    self.drive_service = build('drive', 'v3', credentials=self.google_creds)
                    logger.info("Successfully initialized Google services from file")
                except Exception as e:
                    logger.error(f"Error loading Google credentials from file: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.warning("No Google credentials found")
                
        except Exception as e:
            logger.error(f"Unexpected error in ContentPlannerAPI init: {e}")
            logger.error(traceback.format_exc())

planner = ContentPlannerAPI()

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        "status": "online",
        "service": "Content Planner API",
        "endpoints": ["/health", "/create-google-doc"]
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "google_services_initialized": bool(planner.docs_service and planner.drive_service),
        "environment_vars": {
            "BUBBLE_API_KEY": bool(os.environ.get('BUBBLE_API_KEY')),
            "GOOGLE_CREDENTIALS_JSON": bool(os.environ.get('GOOGLE_CREDENTIALS_JSON')),
            "GOOGLE_CREDENTIALS_JSON_BASE64": bool(os.environ.get('GOOGLE_CREDENTIALS_JSON_BASE64'))
        }
    })

@app.route('/create-google-doc', methods=['POST'])
def create_google_doc():
    """Create Google Doc from Bubble-generated content and grant permissions"""
    try:
        logger.info("Received create-google-doc request")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Data: {request.json}")
        
        # Validate API key
        api_key = request.headers.get('X-API-Key')
        expected_key = os.environ.get('BUBBLE_API_KEY')
        
        if not expected_key:
            logger.error("BUBBLE_API_KEY not set in environment")
            return jsonify({'success': False, 'error': 'Server configuration error - no BUBBLE_API_KEY'}), 500
        
        if api_key != expected_key:
            logger.warning(f"Invalid API key provided")
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        if not planner.docs_service or not planner.drive_service:
            logger.error("Google services not initialized")
            return jsonify({
                'success': False,
                'error': 'Google services not configured'
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