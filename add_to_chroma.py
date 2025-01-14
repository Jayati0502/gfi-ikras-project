# add_to_chroma.py
import chromadb
import json
import html2text

# File paths
INTERNAL_PATH = "/Users/jayatigambhir/ikras_project/src/data/processed/internal/internal.json"
DRAFTS_PATH = "/Users/jayatigambhir/ikras_project/src/data/processed/drafts/drafts.json"
CHROMA_PATH = "/Users/jayatigambhir/ikras_project/src/data/chroma_db"

def get_or_create_collection(client, name):
    """Get existing collection or create new one"""
    try:
        collection = client.get_collection(name)
        print(f"Found existing collection: {name}")
    except:
        print(f"Creating new collection: {name}")
        collection = client.create_collection(name)
    return collection

def add_zendesk_articles(collection, file_path, doc_type):
    """Add Zendesk articles to collection"""
    print(f"\nProcessing {doc_type} articles from {file_path}")
    html_converter = html2text.HTML2Text()
    html_converter.ignore_links = False
    count = 0
    
    try:
        # Load articles
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            articles = data.get('articles', [])
            print(f"Found {len(articles)} articles to process")
        
        # Process in batches
        batch_size = 10
        current_batch = {
            'documents': [],
            'metadatas': [],
            'ids': []
        }
        
        for article in articles:
            try:
                # Filter based on type
                if doc_type == 'internal' and article.get('draft', True):
                    continue
                elif doc_type == 'drafts' and not article.get('draft', False):
                    continue
                
                # Clean HTML content
                content = html_converter.handle(article.get('body', ''))
                if not content.strip():
                    continue
                
                # Prepare document
                doc_text = f"""
                Title: {article.get('title', 'No Title')}
                URL: {article.get('html_url', 'No URL')}
                Labels: {', '.join(article.get('label_names', []))}
                
                Content:
                {content}
                """
                
                # Convert labels to string for metadata
                labels_str = ';'.join(article.get('label_names', []))
                
                current_batch['documents'].append(doc_text)
                current_batch['metadatas'].append({
                    "type": doc_type,
                    "id": str(article['id']),
                    "title": article.get('title', 'No Title'),
                    "url": article.get('html_url', ''),
                    "labels": labels_str,
                    "created_at": article.get('created_at', ''),
                    "updated_at": article.get('updated_at', '')
                })
                current_batch['ids'].append(f"{doc_type}_{article['id']}")
                count += 1
                
                # Add batch if full
                if len(current_batch['documents']) >= batch_size:
                    print(f"Adding batch of {len(current_batch['documents'])} documents...")
                    collection.add(**current_batch)
                    current_batch = {'documents': [], 'metadatas': [], 'ids': []}
            
            except Exception as e:
                print(f"Error processing article {article.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Add remaining documents
        if current_batch['documents']:
            print(f"Adding final batch of {len(current_batch['documents'])} documents...")
            collection.add(**current_batch)
        
        print(f"Successfully added {count} {doc_type} articles")
        return count
        
    except Exception as e:
        print(f"Error processing {doc_type} articles: {str(e)}")
        return 0

def verify_collection(collection):
    """Verify collection contents"""
    try:
        results = collection.query(
            query_texts=["test"],
            n_results=1
        )
        count = len(results['ids'][0])
        print(f"\nCollection: {collection.name}")
        print(f"Total documents: {count}")
        
        if count > 0:
            print("Sample metadata:")
            for key, value in results['metadatas'][0][0].items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error verifying collection: {str(e)}")

def main():
    # Connect to existing ChromaDB
    print(f"Connecting to ChromaDB at: {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Process internal articles
    internal_collection = get_or_create_collection(client, "support_internal")
    internal_count = add_zendesk_articles(internal_collection, INTERNAL_PATH, "internal")
    
    # Process draft articles
    drafts_collection = get_or_create_collection(client, "support_drafts")
    drafts_count = add_zendesk_articles(drafts_collection, DRAFTS_PATH, "drafts")
    
    # Print summary
    print("\nAddition Complete!")
    print("="*50)
    print(f"Internal articles added: {internal_count}")
    print(f"Draft articles added: {drafts_count}")
    print("="*50)
    
    # Verify collections
    print("\nVerifying collections:")
    verify_collection(internal_collection)
    verify_collection(drafts_collection)

if __name__ == "__main__":
    main()
