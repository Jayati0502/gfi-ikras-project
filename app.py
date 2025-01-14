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

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

class SupportSystem:
    def __init__(self):
        logger.info("Initializing SupportSystem...")
        try:
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
            raise

    def get_search_keywords(self, question: str) -> List[str]:
        """Extract keywords from the question using Claude."""
        try:
            response = self.client.completion(
                prompt=f"Extract relevant keywords for the following question: {question}",
                stop_sequences=["\n"],
                max_tokens=50,
                model="claude-v1"
            )
            keywords = response['completion'].split(", ")
            logger.info(f"Extracted keywords: {keywords}")
            return keywords
        except Exception as e:
            logger.error(f"Keyword extraction error: {e}")
            raise

    def search_knowledge_base(self, keywords: List[str]) -> List[Dict]:
        """Perform a semantic search in ChromaDB."""
        try:
            results = []
            for key, collection in self.collections.items():
                query_results = collection.query(
                    query_texts=keywords,
                    n_results=5
                )
                results.extend(query_results['documents'])
            logger.info(f"Search results: {results}")
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise

    def generate_response(self, question: str, articles: List[Dict]) -> str:
        """Generate a draft response using Claude."""
        try:
            references = "\n".join([f"- {article['title']} ({article.get('url', 'No URL')})" for article in articles])
            prompt = f"""
            Question: {question}
            References: 
            {references}
            
            Provide a professional and helpful response, summarizing relevant information from the articles above.
            """
            response = self.client.completion(
                prompt=prompt,
                stop_sequences=["\n"],
                max_tokens=300,
                model="claude-v1"
            )
            return response['completion']
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            raise

    def answer_question(self, question: str) -> Dict:
        """Complete workflow to answer a question."""
        try:
            keywords = self.get_search_keywords(question)
            articles = self.search_knowledge_base(keywords)
            response = self.generate_response(question, articles)
            return {
                "answer": response,
                "references": articles
            }
        except Exception as e:
            logger.error(f"Error in answering question: {e}")
            raise

# Initialize support system
support_system = None
try:
    support_system = SupportSystem()
except Exception as e:
    logger.critical("SupportSystem initialization failed.")

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
    return jsonify({"status": "healthy" if support_system else "failed"})

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
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = 8000  # Hardcoded for debugging
    logger.info(f"Running on hardcoded port: {port}")
    try:
        app.run(host='0.0.0.0', port=port)
    except ValueError as e:
        logger.error(f"Invalid port: {port}. Error: {e}")
        raise

