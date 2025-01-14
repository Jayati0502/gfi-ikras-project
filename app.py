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

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

class SupportSystem:
    def __init__(self):
        logger.info("Starting SupportSystem initialization")
        try:
            # Log environment variables for debugging
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

    def get_search_keywords(self, query: str) -> List[str]:
        """Extract search keywords using Claude"""
        try:
            logger.info(f"Generating keywords for query: {query}")
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": f"""
                    Extract 3-5 key search terms from this support question, 
                    focusing on technical terms and important concepts.
                    Return only the keywords separated by commas, no other text.
                    
                    Question: {query}
                    """
                }]
            )
            keywords = response.content[0].text.strip().split(',')
            keywords = [k.strip() for k in keywords if k.strip()]
            logger.info(f"Generated keywords: {keywords}")
            return keywords
        except Exception as e:
            logger.error(f"Keyword generation error: {e}")
            return [query]

    def search_knowledge_base(self, keywords: List[str], limit: int = 5) -> Dict:
        """Search knowledge base with semantic matching"""
        logger.info(f"Searching with keywords: {keywords}")
        
        all_results = []
        
        for keyword in keywords:
            logger.info(f"Searching for keyword: {keyword}")
            for key, collection in self.collections.items():
                try:
                    results = collection.query(
                        query_texts=[keyword],
                        n_results=3
                    )
                    
                    for doc, meta, distance in zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                    ):
                        relevance = 1 - (distance / 2)
                        if relevance > 0.3:
                            all_results.append((doc, meta, relevance))
                            logger.info(f"Match in {key}: {meta.get('title', '')} ({relevance:.2f})")
                except Exception as e:
                    logger.error(f"Search error in {key}: {e}")
                    continue
        
        if not all_results:
            logger.info("No search results found")
            return {'documents': [], 'metadatas': [], 'relevance_scores': []}
            
        # Remove duplicates and sort
        seen_ids = set()
        unique_results = []
        for doc, meta, score in all_results:
            if meta['id'] not in seen_ids:
                seen_ids.add(meta['id'])
                unique_results.append((doc, meta, score))
        
        # Sort by relevance
        unique_results.sort(key=lambda x: x[2], reverse=True)
        
        # Take top results
        top_results = {
            'documents': [item[0] for item in unique_results[:limit]],
            'metadatas': [item[1] for item in unique_results[:limit]],
            'relevance_scores': [item[2] for item in unique_results[:limit]]
        }
        
        logger.info(f"Found {len(top_results['documents'])} relevant documents")
        return top_results

    def generate_response(self, query: str, context: Dict) -> Dict:
        """Generate response using Claude"""
        try:
            logger.info("Generating response...")
            articles = []
            references = []
            
            for doc, meta, score in zip(
                context['documents'],
                context['metadatas'],
                context['relevance_scores']
            ):
                articles.append({
                    'content': doc,
                    'meta': meta,
                    'score': score
                })
                references.append({
                    "type": meta.get('type', 'article'),
                    "title": meta.get('title', ''),
                    "url": meta.get('url', ''),
                    "id": meta.get('id', ''),
                    "relevance": f"{score:.2f}"
                })
            
            if not articles:
                return {
                    "answer": "I couldn't find any relevant information for your question.",
                    "references": []
                }
            
            context_parts = [f"\nFrom {art['meta'].get('type', 'article')} #{art['meta']['id']}:\n{art['content']}" for art in articles]
            full_context = "\n".join(context_parts)
            
            logger.info("Calling Claude API...")
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""
                    You are a GFI Software support agent. Based on the provided references, help with this question:
                    
                    Customer Question: {query}
                    
                    Reference Material:
                    {full_context}
                    
                    Format your response as:
                    1. Clear, direct answer using information from references
                    2. Any specific steps or procedures mentioned
                    3. Important warnings or requirements
                    4. References to specific articles with their IDs
                    
                    Keep responses focused on reference content but natural and clear.
                    """
                }]
            )
            
            logger.info("Got response from Claude")
            return {
                "answer": response.content[0].text,
                "references": references
            }
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            logger.error(traceback.format_exc())
            return {
                "answer": f"Error generating response: {e}",
                "references": []
            }

    def answer_question(self, query: str) -> Dict:
        """Complete question-answering process"""
        try:
            logger.info(f"Processing question: {query}")
            
            # Get keywords
            keywords = self.get_search_keywords(query)
            
            # Search knowledge base
            search_results = self.search_knowledge_base(keywords)
            
            if not search_results['documents']:
                return {
                    "answer": "I couldn't find any relevant information. Please try rephrasing your question.",
                    "references": []
                }
            
            # Generate response
            return self.generate_response(query, search_results)
            
        except Exception as e:
            logger.error(f"Question processing error: {e}")
            logger.error(traceback.format_exc())
            return {
                "answer": f"Error processing question: {e}",
                "references": []
            }

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
        "collections": len(support_system.collections) if support_system else 0
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
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port)
