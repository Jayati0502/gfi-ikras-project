# setup_chroma.py
import os
import json
import chromadb
import html2text
import gc
import sys
import time
from datetime import datetime

# File paths
ARTICLES_PATH = "/Users/jayatigambhir/ikras_project/src/data/processed/articles/articles.json"
TICKETS_PATH = "/Users/jayatigambhir/ikras_project/src/data/processed/tickets/tickets.json"
CHROMA_PATH = "/Users/jayatigambhir/ikras_project/src/data/chroma_db"

def log_status(message, important=False):
    """Log status with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if important:
        print("\n" + "="*50)
        print(f"[{timestamp}] {message}")
        print("="*50 + "\n")
    else:
        print(f"[{timestamp}] {message}")

def count_json_items(file_path, key):
    """Count total items in JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return len(data.get(key, []))
    except Exception as e:
        log_status(f"Error counting items in {file_path}: {str(e)}")
        return 0

def load_articles(collection):
    """Load articles into ChromaDB with detailed progress"""
    log_status("Starting articles loading process", important=True)
    
    try:
        # Count total articles
        total_articles = count_json_items(ARTICLES_PATH, 'articles')
        log_status(f"Found {total_articles} total articles to process")
        
        # Initialize HTML converter
        log_status("Initializing HTML converter...")
        html_converter = html2text.HTML2Text()
        html_converter.ignore_links = False
        
        # Read articles file
        log_status("Reading articles file...")
        with open(ARTICLES_PATH, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        
        articles = articles_data.get('articles', [])
        count = 0
        batch_size = 10
        start_time = time.time()
        
        documents = []
        metadatas = []
        ids = []
        
        log_status("Beginning article processing...", important=True)
        
        for article in articles:
            if article.get('draft', True):
                continue
                
            try:
                # Clean content
                clean_content = html_converter.handle(article.get('body', ''))
                if not clean_content.strip():
                    continue
                
                doc_text = f"""
                Title: {article.get('title', 'No Title')}
                URL: {article.get('html_url', 'No URL')}
                Labels: {', '.join(article.get('label_names', []))}
                Content: {clean_content}
                """
                
                documents.append(doc_text)
                metadatas.append({
                    "type": "article",
                    "id": str(article['id']),
                    "title": article.get('title', 'No Title'),
                    "url": article.get('html_url', '')
                })
                ids.append(f"article_{article['id']}")
                count += 1
                
                # Add batch to ChromaDB
                if len(documents) >= batch_size:
                    elapsed = time.time() - start_time
                    rate = count / elapsed if elapsed > 0 else 0
                    
                    log_status(f"Adding batch to ChromaDB... ({count}/{total_articles} articles processed, {rate:.2f} articles/sec)")
                    collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    
                    documents = []
                    metadatas = []
                    ids = []
                    gc.collect()
                
            except Exception as e:
                log_status(f"Error processing article {article.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Add remaining documents
        if documents:
            log_status("Adding final batch to ChromaDB...")
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        elapsed = time.time() - start_time
        log_status(f"Articles loading complete! Processed {count} articles in {elapsed:.2f} seconds", important=True)
        
    except Exception as e:
        log_status(f"Fatal error in article loading: {str(e)}", important=True)
        raise
    
    return count

def load_tickets(collection):
    """Load tickets into ChromaDB with detailed progress"""
    log_status("Starting tickets loading process", important=True)
    
    try:
        # Count total tickets
        total_tickets = count_json_items(TICKETS_PATH, 'tickets')
        log_status(f"Found {total_tickets} total tickets to process")
        
        # Read tickets file
        log_status("Reading tickets file...")
        with open(TICKETS_PATH, 'r', encoding='utf-8') as f:
            tickets_data = json.load(f)
        
        tickets = tickets_data.get('tickets', [])
        count = 0
        batch_size = 10
        start_time = time.time()
        
        documents = []
        metadatas = []
        ids = []
        
        log_status("Beginning ticket processing...", important=True)
        
        for ticket in tickets:
            if not ticket.get('description'):
                continue
                
            try:
                doc_text = f"""
                Subject: {ticket.get('subject', 'No Subject')}
                Type: {ticket.get('type', 'No Type')}
                Description: {ticket.get('description', '')}
                """
                
                documents.append(doc_text)
                metadatas.append({
                    "type": "ticket",
                    "id": str(ticket['id']),
                    "subject": ticket.get('subject', 'No Subject')
                })
                ids.append(f"ticket_{ticket['id']}")
                count += 1
                
                # Add batch to ChromaDB
                if len(documents) >= batch_size:
                    elapsed = time.time() - start_time
                    rate = count / elapsed if elapsed > 0 else 0
                    
                    log_status(f"Adding batch to ChromaDB... ({count}/{total_tickets} tickets processed, {rate:.2f} tickets/sec)")
                    collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    
                    documents = []
                    metadatas = []
                    ids = []
                    gc.collect()
                
            except Exception as e:
                log_status(f"Error processing ticket {ticket.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Add remaining documents
        if documents:
            log_status("Adding final batch to ChromaDB...")
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        elapsed = time.time() - start_time
        log_status(f"Tickets loading complete! Processed {count} tickets in {elapsed:.2f} seconds", important=True)
        
    except Exception as e:
        log_status(f"Fatal error in ticket loading: {str(e)}", important=True)
        raise
    
    return count

def main():
    try:
        log_status("Starting ChromaDB setup", important=True)
        
        # Setup ChromaDB
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        log_status(f"ChromaDB will be stored in: {CHROMA_PATH}")
        
        # Create collections
        log_status("Creating collections...")
        try:
            client.delete_collection("support_articles")
            client.delete_collection("support_tickets")
        except:
            pass
            
        articles_collection = client.create_collection("support_articles")
        tickets_collection = client.create_collection("support_tickets")
        
        # Load articles
        articles_count = load_articles(articles_collection)
        log_status(f"Successfully loaded {articles_count} articles", important=True)
        
        # Load tickets
        tickets_count = load_tickets(tickets_collection)
        log_status(f"Successfully loaded {tickets_count} tickets", important=True)
        
        # Final status
        log_status("Setup Complete!", important=True)
        log_status(f"Total articles loaded: {articles_count}")
        log_status(f"Total tickets loaded: {tickets_count}")
        
    except Exception as e:
        log_status(f"Fatal error: {str(e)}", important=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
