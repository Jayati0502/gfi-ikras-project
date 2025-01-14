# migrate_data.py
import chromadb
import os
import shutil

def migrate_data():
    print("Starting migration...")
    
    # Source (your local ChromaDB)
    source_path = "/Users/jayatigambhir/ikras_project/src/data/chroma_db"
    print(f"Source path: {source_path}")
    source_db = chromadb.PersistentClient(path=source_path)
    
    # Destination (for Railway)
    temp_path = "src/data/chroma_db"
    if os.path.exists(temp_path):
        print(f"Removing existing {temp_path}")
        shutil.rmtree(temp_path)
    print(f"Creating {temp_path}")
    os.makedirs(temp_path)
    
    dest_db = chromadb.PersistentClient(path=temp_path)
    
    # Migrate each collection
    collections = ["support_articles", "support_tickets", "support_internal", "support_drafts"]
    
    for coll_name in collections:
        print(f"\nMigrating {coll_name}...")
        try:
            # Get source collection if exists
            try:
                source_collection = source_db.get_collection(coll_name)
                print(f"Found source collection: {coll_name}")
            except Exception as e:
                print(f"Source collection {coll_name} not found: {str(e)}")
                continue
            
            # Create destination collection
            dest_collection = dest_db.create_collection(coll_name)
            print(f"Created destination collection: {coll_name}")
            
            # Get all data from source
            results = source_collection.get()
            
            if results['ids']:
                # Add to destination in smaller batches
                batch_size = 100
                total_docs = len(results['ids'])
                
                for i in range(0, total_docs, batch_size):
                    end_idx = min(i + batch_size, total_docs)
                    print(f"Processing batch {i}-{end_idx} of {total_docs}")
                    
                    dest_collection.add(
                        documents=results['documents'][i:end_idx],
                        metadatas=results['metadatas'][i:end_idx],
                        ids=results['ids'][i:end_idx]
                    )
                print(f"Migrated {total_docs} documents for {coll_name}")
            else:
                print(f"No documents found in {coll_name}")
            
        except Exception as e:
            print(f"Error migrating {coll_name}: {str(e)}")
            continue
    
    print("\nMigration complete!")
    print(f"Data migrated to: {os.path.abspath(temp_path)}")

if __name__ == "__main__":
    migrate_data()
