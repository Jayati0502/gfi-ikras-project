# test_chroma.py
import chromadb

def test_collections():
    db = chromadb.PersistentClient(path="src/data/chroma_db")
    
    collections = ["support_articles", "support_tickets", "support_internal", "support_drafts"]
    
    for coll_name in collections:
        try:
            collection = db.get_collection(coll_name)
            results = collection.query(
                query_texts=["test"],
                n_results=1
            )
            print(f"\nCollection: {coll_name}")
            print(f"Documents found: {len(results['ids'][0])}")
        except Exception as e:
            print(f"Error checking {coll_name}: {str(e)}")

if __name__ == "__main__":
    test_collections()
