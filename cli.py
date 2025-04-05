import argparse
import os
import sys

# Import everything from your existing qdrant.py file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from qdrant import *  # This imports all variables and functions

def main():
    # Create parser
    parser = argparse.ArgumentParser(description='Godot RAG CLI tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query the vector database')
    query_parser.add_argument('text', help='The query text')
    query_parser.add_argument('--limit', type=int, default=3, help='Maximum number of results')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Index a Godot project')
    index_parser.add_argument('path', help='Path to Godot project')
    index_parser.add_argument('--chunk-size', type=int, default=1000, help='Size of text chunks')
    index_parser.add_argument('--overlap', type=int, default=200, help='Overlap between chunks')
    
    # Collection commands
    create_collection_parser = subparsers.add_parser('create-collection', help='Create a new collection')
    create_collection_parser.add_argument('--name', default='godot_game', help='Collection name')
    
    list_collections_parser = subparsers.add_parser('list-collections', help='List all collections')
    
    delete_collection_parser = subparsers.add_parser('delete-collection', help='Delete a collection')
    delete_collection_parser.add_argument('name', help='Collection name')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if args.command == 'query':
        context = get_context_for_query(args.text, args.limit)
        print("\n--- CONTEXT FOR CLAUDE ---")
        print(context)
        print("\n--- END CONTEXT ---")
        
    elif args.command == 'index':
        # Check if collection exists first
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if 'godot_game' not in collection_names:
            print("Collection 'godot_game' doesn't exist. Creating it first...")
            client.create_collection(
                collection_name='godot_game',
                vectors_config=VectorParams(
                    size=model.get_sentence_embedding_dimension(),
                    distance=Distance.COSINE
                )
            )
            
        # Index the project
        stats = index_godot_project(
            project_path=args.path,
            client=client,
            chunk_size=args.chunk_size,
            chunk_overlap=args.overlap
        )
        
    elif args.command == 'create-collection':
        client.create_collection(
            collection_name=args.name,
            vectors_config=VectorParams(
                size=model.get_sentence_embedding_dimension(),
                distance=Distance.COSINE
            )
        )
        print(f"Collection '{args.name}' created successfully!")
        
    elif args.command == 'list-collections':
        collections = client.get_collections()
        if collections.collections:
            print("Available collections:")
            for collection in collections.collections:
                print(f"- {collection.name}")
        else:
            print("No collections found.")
            
    elif args.command == 'delete-collection':
        confirm = input(f"Are you sure you want to delete collection '{args.name}'? (y/n): ")
        if confirm.lower() == 'y':
            client.delete_collection(collection_name=args.name)
            print(f"Collection '{args.name}' deleted.")
        else:
            print("Deletion cancelled.")
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
