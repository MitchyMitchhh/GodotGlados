import argparse
import os
import sys
import subprocess

# Import everything from your existing qdrant.py file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from qdrant import *  # This imports all variables and functions

def query_database(text, limit=3, collections=None):
    """Query multiple collections and combine the results."""
    # If no collections specified, search all available collections
    if collections is None:
        try:
            all_collections = client.get_collections()
            collections = [c.name for c in all_collections.collections]
            print(f"Searching across all collections: {collections}")
        except Exception as e:
            print(f"Error retrieving collections: {e}")
            collections = ["godot_game", "godot_docs"]  # Fallback to defaults
    
    all_context = []
    for collection in collections:
        try:
            # Get context from this collection
            context = get_context_for_query(text, limit, collection)
            if context.strip():
                all_context.append(f"\n--- CONTEXT FROM {collection.upper()} ---")
                all_context.append(context)
        except Exception as e:
            print(f"Error querying collection '{collection}': {e}")
    
    if all_context:
        combined_context = "\n".join(all_context)
        print("\n--- CONTEXT FOR CLAUDE ---")
        print(combined_context)
        print("\n--- END CONTEXT ---")
        return combined_context
    else:
        print("No relevant context found in any collection.")
        return ""

def index_project(path=r"C:\Users\Mitch\Game Dev\Emergency-Hotfix", chunk_size=1000, chunk_overlap=200):
    """Index a Godot project into the vector database."""
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    if 'godot_game' not in collection_names:
        print("Collection 'godot_game' doesn't exist. Creating it first...")
        create_collection('godot_game')
    
    stats = index_godot_project(
        project_path=path,
        client=client,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return stats

def create_collection(name):
    """Create a new vector collection."""
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=model.get_sentence_embedding_dimension(),
            distance=Distance.COSINE
        )
    )
    print(f"Collection '{name}' created successfully!")

def list_collections():
    """List all available collections."""
    collections = client.get_collections()
    if collections.collections:
        print("Available collections:")
        for collection in collections.collections:
            print(f"- {collection.name}")
    else:
        print("No collections found.")

def delete_collection(name):
    """Delete a collection after confirmation."""
    confirm = input(f"Are you sure you want to delete collection '{name}'? (y/n): ")
    if confirm.lower() == 'y':
        client.delete_collection(collection_name=name)
        print(f"Collection '{name}' deleted.")
    else:
        print("Deletion cancelled.")

def add_godot_docs(version="stable", collection_name="godot_docs"):
    """Clone and index Godot documentation."""
    # Clone repo (shallow clone to save space/time)
    docs_path = "godot-docs-temp"
    os.makedirs(docs_path, exist_ok=True)
    
    print(f"Cloning Godot docs ({version} branch)...")
    subprocess.run(["git", "clone", "--depth", "1", "-b", version, 
                   "https://github.com/godotengine/godot-docs.git", docs_path])
    
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    if collection_name not in collection_names:
        print(f"Collection '{collection_name}' doesn't exist. Creating it first...")
        create_collection(collection_name)
    
    # Index the documentation (focusing on classes directory for API reference)
    print("Indexing documentation...")
    stats = index_godot_project(
        project_path=os.path.join(docs_path, "classes"),
        client=client,
        collection_name=collection_name,
        file_extensions=[".rst", ".md", ".txt"]
    )
    
    print(f"Indexed {stats['files_processed']} documentation files.")
    return stats

def setup_parser():
    """Configure the command line argument parser."""
    parser = argparse.ArgumentParser(description='Godot RAG CLI tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    query_parser = subparsers.add_parser('query', help='Query the vector database')
    query_parser.add_argument('text', help='The query text')
    query_parser.add_argument('--limit', type=int, default=3, help='Maximum number of results')
    query_parser.add_argument('--collections', nargs='+', choices=['godot_game', 'godot_docs', 'all'], default=['all'], help='Collections to search')
    
    index_parser = subparsers.add_parser('index', help='Index a Godot project')
    index_parser.add_argument('--path', type=str, default=r"C:\Users\Mitch\Game Dev\Emergency-Hotfix", help='Path to Godot project')
    index_parser.add_argument('--chunk-size', type=int, default=1000, help='Size of text chunks')
    index_parser.add_argument('--overlap', type=int, default=200, help='Overlap between chunks')
    
    create_collection_parser = subparsers.add_parser('create-collection', help='Create a new collection')
    create_collection_parser.add_argument('--name', default='godot_game', help='Collection name')
    
    list_collections_parser = subparsers.add_parser('list-collections', help='List all collections')
    
    delete_collection_parser = subparsers.add_parser('delete-collection', help='Delete a collection')
    delete_collection_parser.add_argument('name', help='Collection name')
    
    docs_parser = subparsers.add_parser('add-docs', help='Add Godot documentation to the RAG system')
    docs_parser.add_argument('--version', default='stable', help='Doc version (branch name)')
    docs_parser.add_argument('--collection', default='godot_docs', help='Collection name for docs')
    
    return parser

def main():
    """Main entry point for the CLI."""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == 'query':
        query_database(args.text, args.limit)
        
    elif args.command == 'index':
        index_project(args.path, args.chunk_size, args.overlap)
        
    elif args.command == 'create-collection':
        create_collection(args.name)
        
    elif args.command == 'list-collections':
        list_collections()
            
    elif args.command == 'delete-collection':
        delete_collection(args.name)
    
    elif args.command == 'add-docs':
        add_godot_docs(args.version, args.collection)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
