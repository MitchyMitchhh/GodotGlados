import argparse
import os
import sys
import subprocess
import pyperclip

# Import everything from your existing qdrant.py file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from qdrant import *  # This imports all variables and functions

def query_database(text, limit=3, collections=None, include_rules=False, update_project=False):
    """Query multiple collections and combine the results."""
    all_context = []
    all_context.append(f"Prompt: {text}")
    project_rules = None
    if update_project:
        print('Updating Godot project file index')
        index_project()
    if include_rules:
        try:
            rules_context = None
            rules_file_path = os.path.join(os.path.dirname(__file__), "project_rules.md")
            if os.path.exists(rules_file_path):
                with open(rules_file_path, 'r') as f:
                    rules_context = f.read()
            else:
                rules_context = get_context_for_query("project coding standards rules", 1, "godot_game")

            project_rules = rules_context
            all_context.append("--- PROJECT RULES ---\n\n" + rules_context + "\n")

        except Exception as e:
            print(f"Error retrieving project rules: {e}")
    
    if collections is None:
        try:
            all_collections = client.get_collections()
            collections = [c.name for c in all_collections.collections]
            print(f"Searching across all collections: {collections}")
        except Exception as e:
            print(f"Error retrieving collections: {e}")
            collections = ["godot_game", "godot_docs"]
    
    for collection in collections:
        try:
            context = get_context_for_query(text, limit, collection)
            if context.strip():
                all_context.append(f"\n--- CONTEXT FROM {collection.upper()} ---")
                all_context.append(context)
        except Exception as e:
            print(f"Error querying collection '{collection}': {e}")
    
    if all_context:
        combined_context = "\n\n".join(all_context)
        print("\n--- CONTEXT FOR LLM ---")
        print(combined_context)
        print("\n--- END CONTEXT ---")
        try:
            pyperclip.copy(combined_context)
            print("Context copied to clipboard!")
        except:
            print("Could not copy")
            pass
        return combined_context, project_rules
    else:
        print("No relevant context found in any collection.")
        return "", ""

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

def index_godot_docs(version="stable", collection_name="godot_docs"):
    """Clone and index Godot documentation."""
    # Clone repo (shallow clone to save space/time)
    docs_path = "godot-docs-temp"
    
    if os.path.exists(docs_path):
        print(f"Directory {docs_path} already exists. Updating instead of cloning...")
        # Update the repo
        subprocess.run(["git", "-C", docs_path, "pull"])
    else:
        # Directory doesn't exist, so create parent directories if needed
        os.makedirs(os.path.dirname(docs_path), exist_ok=True)
        
        # Clone if doesn't exist
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
    query_parser.add_argument('--collections', nargs='+', choices=['godot_game', 'godot_docs'], default=None, help='Collections to search')
    query_parser.add_argument('--rules', action='store_true', help='Include project rules in context')
    query_parser.add_argument('--update_project', action='store_true', help='Update Godot Project Index')
        
    index_parser = subparsers.add_parser('index-project', help='Index a Godot project')
    index_parser.add_argument('--path', type=str, default=r"C:\Users\Mitch\Game Dev\Emergency-Hotfix", help='Path to Godot project')
    index_parser.add_argument('--chunk-size', type=int, default=1000, help='Size of text chunks')
    index_parser.add_argument('--overlap', type=int, default=200, help='Overlap between chunks')
    
    docs_parser = subparsers.add_parser('index-docs', help='Index Godot documentation to the RAG system')
    docs_parser.add_argument('--version', default='stable', help='Doc version (branch name)')
    docs_parser.add_argument('--collection', default='godot_docs', help='Collection name for docs')
    
    create_collection_parser = subparsers.add_parser('create-collection', help='Create a new collection')
    create_collection_parser.add_argument('--name', default='godot_game', help='Collection name')
    
    list_collections_parser = subparsers.add_parser('list-collections', help='List all collections')
    
    delete_collection_parser = subparsers.add_parser('delete-collection', help='Delete a collection')
    delete_collection_parser.add_argument('name', help='Collection name')
    
   
    return parser

def main():
    """Main entry point for the CLI."""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == 'query':
        query_database(args.text, args.limit, args.collections, args.rules, args.update_project)
        
    elif args.command == 'index-project':
        index_project(args.path, args.chunk_size, args.overlap)

    elif args.command == 'index-docs':
        index_godot_docs(args.version, args.collection)
        
    elif args.command == 'create-collection':
        create_collection(args.name)
        
    elif args.command == 'list-collections':
        list_collections()
            
    elif args.command == 'delete-collection':
        delete_collection(args.name)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
