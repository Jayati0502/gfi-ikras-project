# add_collections.py
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

def load_json_file(file_path):
    """Load and parse JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            print(f"Reading {file_path}...")
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        return None

def add_documents(collection, data, doc_type):
    """Add documents to collection"""
    html_converter = html2text.HTML2Text()
    html_converter.ignore_links = False
    count = 0

    # Convert to list if single document
    documents = data if isinstance(data, list) else [data]
    
    # Process in batches
    batch_size = 10
    current_docs = []
    current_metadatas = []
    current_ids = []

    for doc in documents:
        try:
            # Clean and prepare content
            content = html_converter.handle(doc.get('body', '') or doc.get('content', ''))
            if not content.strip():
                continue

            doc_text = f"""
            Title: {doc.get('title', 'No Title')}
            Type: {doc_type}
            Content: {content}
            """

            current_docs.append(doc_text)
            current_metadatas.append({
                "type": doc_type,
                "id": str(doc.get('id', f"{doc_type}_{count}")),
                "title": doc.get('title', 'No Title')
            })
            current_ids.append(f"{doc_type}_{count}")
            count += 1

            # Add batch if full
            if len(current_docs) >= batch_size:
                collection.add(
                    documents=current_docs,
                    metadatas=current_metadatas,
                    ids=current_ids
                )
                print(f"Added batch of {len(current_docs)} {doc_type} documents")
                current_docs = []
                current_metadatas = []
                current_ids = []

        except Exception as e:
            print(f"Error processing document: {str(e)}")
            continue

    # Add remaining documents
    if current_docs:
        collection.add(
            documents=current_docs,
            metadatas=current_metadatas,
            ids=current_ids
        )
        print(f"Added final batch of {len(current_docs)} {doc_type} documents")

    return count

def main():
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    results = {}

    # Process internal documents
    print("\nProcessing internal documents...")
    internal_data = load_json_file(INTERNAL_PATH)
    if internal_data:
        internal_collection = setup_collection(client, "internal")
        count = add_documents(internal_collection, internal_data, "internal")
        results["internal"] = count

    # Process drafts
    print("\nProcessing drafts...")
    drafts_data = load_json_file(DRAFTS_PATH)
    if drafts_data:
        drafts_collection = setup_collection(client, "drafts")
        count = add_documents(drafts_collection, drafts_data, "drafts")
        results["drafts"] = count

    # Print summary
    print("\nLoading Complete!")
    print("="*50)
    for doc_type, count in results.items():
        print(f"{doc_type.title()}: {count} documents loaded")
    print("="*50)

    # Verify collections
    print("\nVerifying collections...")
    for doc_type in ["internal", "drafts"]:
        try:
            collection = client.get_collection(f"support_{doc_type}")
            results = collection.query(
                query_texts=["test"],
                n_results=1
            )
            print(f"{doc_type.title()} collection: {len(results['ids'][0])} documents found")
        except Exception as e:
            print(f"Error verifying {doc_type} collection: {str(e)}")

if __name__ == "__main__":
    main()
