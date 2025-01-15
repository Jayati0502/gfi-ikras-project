import os
import logging
import sys
import traceback
from flask import Flask, request, jsonify
import chromadb
from chromadb.config import Settings
from anthropic import Anthropic
from dotenv import load_dotenv
from typing import List, Dict

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

# Initialize Flask app
app = Flask(__name__)

class SupportSystem:
    def __init__(self):
        logger.info("Initializing SupportSystem...")
        try:
            # Log all environment variables for debugging
            logger.info("Environment Variables:")
            for key, value in os.environ.items():
                logger.debug(f"ENV: {key} = {'*****' if 'KEY' in key else value}")

            # Initialize ChromaDB
            db_directory = "/app/data/chroma_db"
            os.makedirs(db_directory, exist_ok=True)
            self.db = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=db_directory
            ))

            self.collections = {
                key: self.db.get_or_create_collection(name)
                for key, name in {
                    'articles': 'support_articles',
                    'tickets': 'support_tickets',
                    'internal': 'support_internal',
                    'drafts': 'support_drafts'
                }.items()
            }

            # Initialize Claude (Anthropic API)
            self.client = Anthropic(os.getenv('ANTHROPIC_API_KEY'))

            logger.info("SupportSystem initialized successfully.")
        except Exception as e:
            logger.critical(f"Initialization error: {e}")
            logger.critical(traceback.format_exc())
            raise

    # [Rest of the methods remain the same as in your previous implementation]

# Initialize support system
support_system = None
try:
    support_system = SupportSystem()
except Exception as e:
    logger.critical(f"SupportSystem initialization failed: {e}")

@app.route('/')
def home():
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
    """Health check endpoint."""
    return jsonify({
        "status": "healthy" if support_system else "failed",
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform
        }
    })

@app.route('/answer', methods=['POST'])
def get_answer():
    """Endpoint to get an answer for a question."""
    try:
        if support_system is None:
            return jsonify({"error": "Support system not initialized"}), 500

        data = request.json
        question = data.get('question', '')
        if not question:
            return jsonify({"error": "No question provided"}), 400

        result = support_system.answer_question(question)
        return jsonify({
            "status": "success",
            "data": {
                "question": question,
                "response": result['answer'],
                "references": result['references']
            }
        })
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def get_port():
    """Dynamically get port from Railway or use a fallback"""
    try:
        # Railway dynamically assigns a PORT
        port_str = os.getenv('PORT', None)
        
        if port_str is None:
            logger.warning("No PORT environment variable found. Using default.")
            return 5001
        
        port = int(port_str)
        if 0 <= port <= 65535:
            return port
        
        logger.warning(f"Invalid PORT {port}, using default")
        return 5001
    except ValueError:
        logger.warning("PORT is not a valid integer")
        return 5001

if __name__ == '__main__':
    # Explicitly log all environment variables for debugging
    logger.info("Startup Environment Variables:")
    for key, value in os.environ.items():
        logger.debug(f"ENV: {key} = {'*****' if 'KEY' in key else value}")
    
    port = get_port()
    host = '0.0.0.0'
    
    logger.info(f"Starting application on {host}:{port}")
    
    # Ensure logging is flushed
    logging.getLogger().handlers[0].flush()
    
    # Run the application
    app.run(host=host, port=port)
