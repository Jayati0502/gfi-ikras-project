# add_zendesk_collections.py
import chromadb
import json
import html2text

# File paths
INTERNAL_PATH = "/Users/jayatigambhir/ikras_project/src/data/processed/internal/internal.json"
DRAFTS_PATH = "/Users/jayatigambhir/ikras_project/src/data/processed/drafts/drafts.json"
CHROMA_PATH = "/Users/jayatigambhir/ikras_project/src/data/chroma_db"

def setup_collection(client, name):
    """Create or reset a collection"""
    try:
        client.delete_collection(f"support_{name}")
    except:
        pass
    collection = client.create_collection(f"support_{name}")
    print(f"Created collection: support_{name}")
    return collection

def load_zendesk_articles(file_path):
    """Load articles from Zendesk JSON format"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            print(f"Reading {file_path}...")
            data = json.load(f)
            articles = data.get('articles', [])
            print(f"Found {len(articles)} articles in file")
            return articles
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        return []

def process_articles(collection, articles, doc_type):
    """Process and add articles to collection"""
    html_converter = html2text.HTML2Text()
    html_converter.ignore_links = False
    count = 0

    # Process in batches
    batch_size = 10
    current_batch = {
        'documents': [],
        'metadatas': [],
        'ids': []
    }

    for article in articles:
        try:
            # Skip drafts based on the collection type
            if doc_type == 'internal' and article.get('draft', True):
                continue
            elif doc_type == 'drafts' and not article.get('draft', False):
                continue

            # Clean HTML content
            content = html_converter.handle(article.get('body', ''))
            if not content.strip():
                continue

            # Prepare document text
            doc_text = f"""
            Title: {article.get('title', 'No Title')}
            URL: {article.get('html_url', 'No URL')}
            Labels: {', '.join(article.get('label_names', []))}
            
            Content:
            {content}
            """

            current_batch['documents'].append(doc_text)
            current_batch['metadatas'].append({
                "type": doc_type,
                "id": str(article['id']),
                "title": article.get('title', 'No Title'),
                "url": article.get('html_url', ''),
                "labels": article.get('label_names', [])
            })
            current_batch['ids'].append(f"{doc_type}_{article['id']}")
            count += 1

            # Add batch if full
            if len(current_batch['documents']) >= batch_size:
                print(f"Adding batch of {len(current_batch['documents'])} {doc_type} documents...")
                collection.add(**current_batch)
                current_batch = {'documents': [], 'metadatas': [], 'ids': []}

        except Exception as e:
            print(f"Error processing article {article.get('id', 'unknown')}: {str(e)}")
            continue

    # Add remaining documents
    if current_batch['documents']:
        print(f"Adding final batch of {len(current_batch['documents'])} {doc_type} documents...")
        collection.add(**current_batch)

    return count

def main():
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Process internal articles
    print("\nProcessing internal articles...")
    internal_collection = setup_collection(client, "internal")
    internal_articles = load_zendesk_articles(INTERNAL_PATH)
    internal_count = process_articles(internal_collection, internal_articles, "internal")

    # Process draft articles
    print("\nProcessing draft articles...")
    drafts_collection = setup_collection(client, "drafts")
    draft_articles = load_zendesk_articles(DRAFTS_PATH)
    drafts_count = process_articles(drafts_collection, draft_articles, "drafts")

    # Print summary
    print("\nLoading Complete!")
    print("="*50)
    print(f"Internal articles: {internal_count} documents loaded")
    print(f"Draft articles: {drafts_count} documents loaded")
    print("="*50)

    # Verify collections
    print("\nVerifying collections...")
    for name in ["internal", "drafts"]:
        try:
            collection = client.get_collection(f"support_{name}")
            results = collection.query(
                query_texts=["test"],
                n_results=1
            )
            print(f"{name.title()} collection: {len(results['ids'][0])} documents found")
        except Exception as e:
            print(f"Error verifying {name} collection: {str(e)}")

if __name__ == "__main__":
    main()
