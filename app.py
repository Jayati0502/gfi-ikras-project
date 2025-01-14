# app.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from typing import Dict, List
from flask import Flask, request, jsonify
import chromadb
from chromadb.config import Settings
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

class SupportSystem:
    def __init__(self):
        print("Initializing support system...")
        try:
            # Initialize ChromaDB with Railway PostgreSQL
            db_url = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
            
            print("Connecting to ChromaDB...")
            self.db = chromadb.PersistentClient(
                settings=Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory="/tmp/chromadb"  # Temporary storage
                )
            )
            
            # Initialize collections
            print("Getting collections...")
            try:
                self.articles = self.db.get_collection("support_articles")
            except:
                self.articles = self.db.create_collection("support_articles")
                
            try:
                self.tickets = self.db.get_collection("support_tickets")
            except:
                self.tickets = self.db.create_collection("support_tickets")
                
            try:
                self.internal = self.db.get_collection("support_internal")
            except:
                self.internal = self.db.create_collection("support_internal")
                
            try:
                self.drafts = self.db.get_collection("support_drafts")
            except:
                self.drafts = self.db.create_collection("support_drafts")

            # Initialize Anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found")
            print("Initializing Anthropic client...")
            self.client = Anthropic(api_key=api_key)
            
            print("Support system ready!")
            
        except Exception as e:
            print(f"Error during initialization: {str(e)}")
            raise

    # [Rest of your existing methods stay the same]

# Initialize the support system
support_system = SupportSystem()

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
    return jsonify({"status": "healthy"})

@app.route('/answer', methods=['POST'])
def get_answer():
    """Get answer for a question"""
    try:
        data = request.json
        if not data or 'question' not in data:
            return jsonify({
                "error": "No question provided"
            }), 400
        
        question = data['question']
        print(f"\nReceived question: {question}")
        
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
                            if ref['type'] == 'article'
                        ],
                        "tickets": [
                            {
                                "id": ref['id'],
                                "title": ref['title'],
                                "relevance": ref['relevance']
                            }
                            for ref in result['references']
                            if ref['type'] == 'ticket'
                        ]
                    }
                }
            }
        })
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
