from flask import Flask, request, jsonify
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for Bubble integration

class ContentPlannerAPI:
    def __init__(self):
        # Initialize Google services only
        self.docs_service = None
        self.drive_service = None
        
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
                print("Successfully initialized Google services from environment variable")
            except Exception as e:
                print(f"Error loading Google credentials from environment: {e}")
        
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
                print("Successfully initialized Google services from JSON environment variable")
            except Exception as e:
                print(f"Error loading Google credentials from JSON env: {e}")
                
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
                print("Successfully initialized Google services from file")
            except Exception as e:
                print(f"Error loading Google credentials from file: {e}")
        else:
            print("Warning: No Google credentials found")

planner = ContentPlannerAPI()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "google_services_initialized": bool(planner.docs_service and planner.drive_service)
    })

@app.route('/create-google-doc', methods=['POST'])
def create_google_doc():
    """Create Google Doc from Bubble-generated content and grant permissions"""
    try:
        # Validate API key
        api_key = request.headers.get('X-API-Key')
        if api_key != os.environ.get('BUBBLE_API_KEY'):
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        if not planner.docs_service or not planner.drive_service:
            return jsonify({
                'success': False,
                'error': 'Google services not configured'
            }), 503
        
        data = request.json
        content_plan = data.get('content_plan')
        user_email = data.get('user_email')
        
        if not content_plan or not user_email:
            return jsonify({
                'success': False,
                'error': 'Content plan and user email are required'
            }), 400
        
        # Create Google Doc
        document = planner.docs_service.documents().create(
            body={'title': f"Short-form Content Plan: {content_plan.get('title', 'Untitled')}"}  
        ).execute()
        
        document_id = document['documentId']
        
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
        
        # Generate share link
        share_link = f"https://docs.google.com/document/d/{document_id}/edit"
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'share_link': share_link
        })
    
    except Exception as e:
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