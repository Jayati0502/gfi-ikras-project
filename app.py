import os
import logging
import sys
import traceback
from typing import Dict, List

from flask import Flask, request, jsonify
import chromadb
from chromadb.config import Settings
from anthropic import Anthropic
from dotenv import load_dotenv

# Enhanced Logging Configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app_logs.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

# Log system information
logger.info(f"Python Version: {sys.version}")
logger.info(f"Platform: {sys.platform}")

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

class SupportSystem:
    def __init__(self):
        logger.info("Starting SupportSystem initialization")
        try:
            # Log all environment variables
            logger.info("Environment Variables:")
            for key, value in os.environ.items():
                logger.debug(f"ENV: {key} = {'*****' if 'KEY' in key else value}")

            # Initialize ChromaDB
            logger.info("Setting up ChromaDB...")
            db_directory = "/app/data/chroma_db"
            os.makedirs(db_directory, exist_ok=True)
            
            logger.info(f"ChromaDB Directory: {db_directory}")
            
            # ChromaDB Client Initialization
            self.db = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=db_directory
            ))
            
            # Collection Initialization
            collections = {
                'articles': 'support_articles',
                'tickets': 'support_tickets',
                'internal': 'support_internal',
                'drafts': 'support_drafts'
            }
            
            self.collections = {}
            for key, name in collections.items():
                try:
                    logger.info(f"Preparing collection: {name}")
                    self.collections[key] = self.db.get_or_create_collection(name)
                    logger.info(f"Collection {name} ready")
                except Exception as e:
                    logger.error(f"Collection {name} initialization error: {e}")
                    logger.error(traceback.format_exc())
            
            # Anthropic Client Initialization
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY is missing")
            
            logger.info("Initializing Anthropic client...")
            self.client = Anthropic(api_key=api_key)
            
            logger.info("SupportSystem initialization complete")
        
        except Exception as e:
            logger.critical(f"Fatal initialization error: {e}")
            logger.critical(traceback.format_exc())
            raise

    # [Rest of the methods remain the same as in the previous version]
    # (get_search_keywords, search_knowledge_base, generate_response, answer_question)
    # ... [previous methods would be identical]

# Global exception handler
def handle_exception(exc_type, exc_value, exc_traceback):
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# Initialize support system
try:
    support_system = SupportSystem()
except Exception as e:
    logger.critical(f"Failed to initialize support system: {e}")
    support_system = None

@app.route('/', methods=['GET'])
def home():
    """Home page"""
    return """
    <h1>GFI Support Assistant</h1>
    <p>API Endpoints:</p>
    <ul>
        <li>/health - Health check</li>
        <li>/answer - Get answer (POST)</li>
    </ul>
    """

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    status = "healthy" if support_system is not None else "initialization_failed"
    return jsonify({
        "status": status,
        "collections": len(support_system.collections) if support_system else 0,
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform
        }
    })

@app.route('/answer', methods=['POST'])
def get_answer():
    """Get answer for a question"""
    try:
        if support_system is None:
            return jsonify({
                "status": "error",
                "message": "Support system not initialized"
            }), 500

        data = request.json
        if not data or 'question' not in data:
            return jsonify({
                "error": "No question provided"
            }), 400
        
        question = data['question']
        logger.info(f"Received question: {question}")
        
        result = support_system.answer_question(question)
        
        return jsonify({
            "status": "success",
            "data": {
                "question": question,
                "response": {
                    "answer": result['answer'].strip(),
                    "references": {
                        "articles": [
                            {
                                "id": ref['id'],
                                "title": ref['title'],
                                "url": ref.get('url', ''),
                                "relevance": ref['relevance']
                            }
                            for ref in result['references']
                        ]
                    }
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Request processing error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    # Explicitly log all environment variables for debugging
    logger.info("Startup Environment Variables:")
    for key, value in os.environ.items():
        logger.debug(f"ENV: {key} = {'*****' if 'KEY' in key else value}")
    
    # Hardcode port to 8080 for Railway
    port = 8080
    host = '0.0.0.0'
    
    logger.info(f"Starting application on {host}:{port}")
    
    # Ensure logging is flushed
    logging.getLogger().handlers[0].flush()
    
    # Run the application
    app.run(host=host, port=port)
