from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer 
import os
from dotenv import load_dotenv
import uuid
import glob
from pathlib import Path
from typing import List, Dict, Any

# Set this in your terminal before running the script
# Windows: set QDRANT_API_KEY=your-key-here
load_dotenv()
api_key = os.environ.get("QDRANT_API_KEY")
QDRANT_URL = "https://401a1d8d-9b06-41b9-b8b3-5c839ac6d254.us-east-1-0.aws.cloud.qdrant.io"

client = QdrantClient(
    url=QDRANT_URL,
    api_key=api_key,
)

# Initialize embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")
godot_project_path = r"C:\Users\Mitch\Game Dev\Emergency-Hotfix"

def index_godot_project(
    project_path: str,
    client: QdrantClient,
    collection_name: str = "godot_game",
    model: SentenceTransformer = None,
    file_extensions: List[str] = [".gd", ".md", ".txt", ".cfg"],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
):
    """
    Index a Godot project directory into a Qdrant vector database.
    
    Args:
        project_path: Path to the Godot project root directory
        client: Initialized QdrantClient
        collection_name: Name of the collection to add documents to
        model: SentenceTransformer model (will be initialized if None)
        file_extensions: List of file extensions to index
        chunk_size: Size of text chunks in characters
        chunk_overlap: Overlap between chunks in characters
    
    Returns:
        dict: Summary of indexing results
    """
    # Initialize model if not provided
    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Statistics
    stats = {
        "files_processed": 0,
        "chunks_created": 0,
        "errors": 0
    }
    
    print(f"Starting to index Godot project at: {project_path}")
    
    # Find all relevant files
    for extension in file_extensions:
        file_pattern = os.path.join(project_path, f"**/*{extension}")
        files = glob.glob(file_pattern, recursive=True)
        
        print(f"Found {len(files)} {extension} files")
        
        # Process files in batches to avoid memory issues
        batch_size = 10
        for i in range(0, len(files), batch_size):
            batch_files = files[i:i+batch_size]
            batch_points = []
            
            for file_path in batch_files:
                try:
                    # Get relative path for cleaner source reference
                    rel_path = os.path.relpath(file_path, project_path)
                    
                    # Skip files in certain directories
                    if any(skip_dir in rel_path for skip_dir in [".git", ".import", "addons"]):
                        continue
                    
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    
                    # Skip empty files
                    if not content.strip():
                        continue
                    
                    # Create chunks with overlap
                    chunks = []
                    for start_idx in range(0, len(content), chunk_size - chunk_overlap):
                        end_idx = min(start_idx + chunk_size, len(content))
                        chunk = content[start_idx:end_idx]
                        if len(chunk.strip()) > 50:  # Skip chunks that are too small
                            chunks.append(chunk)
                    
                    # Process each chunk
                    for i, chunk in enumerate(chunks):
                        # Create embedding
                        embedding = model.encode(chunk).tolist()
                        
                        # Create metadata
                        metadata = {
                            "source": rel_path,
                            "text": chunk,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "file_type": os.path.splitext(file_path)[1][1:],  # Extension without dot
                        }
                        
                        # Add point
                        batch_points.append(
                            PointStruct(
                                id=stats["chunks_created"] + len(batch_points) + 1,  # Numeric ID
                                vector=embedding,
                                payload=metadata
                            )
                        )
                    
                    stats["files_processed"] += 1
                    stats["chunks_created"] += len(chunks)
                    
                    if stats["files_processed"] % 10 == 0:
                        print(f"Processed {stats['files_processed']} files...")
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    stats["errors"] += 1
            
            # Upload batch
            if batch_points:
                try:
                    client.upsert(
                        collection_name=collection_name,
                        points=batch_points
                    )
                    print(f"Uploaded batch of {len(batch_points)} chunks")
                except Exception as e:
                    print(f"Error uploading batch: {e}")
                    stats["errors"] += 1
    
    print("\nIndexing complete!")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Chunks created: {stats['chunks_created']}")
    print(f"Errors: {stats['errors']}")
    
    return stats

def create_collection():
    client.recreate_collection(
        collection_name="godot_game",
        vectors_config=VectorParams(
            size=model.get_sentence_embedding_dimension(),  # Usually 384 for this model
            distance=Distance.COSINE
        )
    )

# Function to add a file to the vector database
def index_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Split into chunks (adjust chunk size as needed)
            chunk_size = 1000
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            
            points = []
            for i, chunk in enumerate(chunks):
                # Generate embedding for this chunk
                embedding = model.encode(chunk).tolist()
                
                # Create a point
                points.append(
                    PointStruct(
                        id=f"{file_path.replace('/', '_')}_{i}",
                        vector=embedding,
                        payload={
                            "text": chunk,
                            "source": file_path,
                            "chunk_index": i
                        }
                    )
                )
            
            # Upload points in batch
            if points:
                client.upsert(
                    collection_name="godot_game",
                    points=points
                )
                print(f"Indexed {len(points)} chunks from {file_path}")
                
    except Exception as e:
        print(f"Error indexing {file_path}: {e}")

# Function to find relevant context for a query
def get_context_for_query(query, limit=3):
    # Encode the query
    query_vector = model.encode(query).tolist()
    
    search_result = client.query_points(
        collection_name="godot_game",
        query=query_vector,
        limit=limit
    ).points
    
    # Format the results as context
    context = ""
    for point in search_result:
        context += f"\n--- From {point.payload.get('source', 'unknown')} ---\n"
        context += point.payload.get('text', 'No text available') + "\n"
        context += f"(Relevance score: {point.score:.4f})\n"
    print(context)
    return context

# Add test data to your collection
def add_test_data():
    print("Adding test Godot game data...")
    
    # Sample Godot documentation snippets
    test_documents = [
        {
            "text": "Player movement in Godot is typically handled by accessing the Input class and applying forces or velocity to the player character's physics body. For example, in GDScript you might use: if Input.is_action_pressed('ui_right'): velocity.x = SPEED.",
            "source": "movement_tutorial.gd"
        },
        {
            "text": "Godot's physics system includes KinematicBody2D, RigidBody2D, and StaticBody2D. KinematicBody2D is best for player-controlled characters as it allows for precise movement control.",
            "source": "physics_overview.md"
        },
        {
            "text": "Camera follow in Godot can be implemented by setting the camera's global_position to the player's position each frame, optionally with smoothing: camera.global_position = camera.global_position.linear_interpolate(player.global_position, 0.1).",
            "source": "camera_system.gd"
        }
    ]
    
    # Create points from documents
    points = []
    for i, doc in enumerate(test_documents):
        # Encode text to vector
        vector = model.encode(doc["text"]).tolist()
        
        # Create point with UUID
        point_id = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=i+1,  # Using numeric ID for simplicity
                vector=vector,
                payload=doc
            )
        )
    
    # Add points to collection
    client.upsert(
        collection_name="godot_game",
        points=points
    )
    
    print(f"Added {len(points)} documents to 'godot_game' collection!")
    
def run_godot_index():
    # Check if collection exists
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    if "godot_game" not in collection_names:
        print("Collection 'godot_game' doesn't exist. Creating it...")
        from qdrant_client.models import VectorParams, Distance
        
        client.create_collection(
            collection_name="godot_game",
            vectors_config=VectorParams(
                size=model.get_sentence_embedding_dimension(),
                distance=Distance.COSINE
            )
        )
    
    # Index the project
    index_godot_project(
        project_path=godot_project_path,
        client=client,
        collection_name="godot_game",
        model=model,
        file_extensions=[".gd", ".md", ".txt", ".cfg", ".json"],
        chunk_size=1000,
        chunk_overlap=200
    )
    
    # Test a query
    print("\nTesting a query...")
    query = "How do I implement player movement?"
    query_vector = model.encode(query).tolist()
    
    response = client.query_points(
        collection_name="godot_game",
        query=query_vector,
        limit=3
    )
    
    print(f"Found {len(response.points)} relevant documents:")
    for i, point in enumerate(response.points):
        print(f"\nResult {i+1}:")
        print(f"Source: {point.payload['source']}")
        print(f"Text: {point.payload['text'][:150]}...")
        print(f"Score: {point.score:.4f}")

# Example usage
if __name__ == "__main__":
    run_godot_index()
    # First time setup
    # create_collection()
    
    # Index some files
    # index_file("player.gd")
    # index_file("game_rules.md")
    # print("Testing Qdrant connection...")
    #
    # try:
    #     # Check collections
    #     collections = client.get_collections()
    #     print(f"Connected successfully! Available collections: {collections}")
    #
    #     # Check if godot_game exists
    #     collection_names = [c.name for c in collections.collections]
    #     if "godot_game" not in collection_names:
    #         print("Collection 'godot_game' doesn't exist. Creating it now...")
    #
    #         # Create the collection
    #         client.create_collection(
    #             collection_name="godot_game",
    #             vectors_config=VectorParams(
    #                 size=model.get_sentence_embedding_dimension(),
    #                 distance=Distance.COSINE
    #             )
    #         )
    #         print("Collection created successfully!")
    #
    #         # Add some test data if you want
    #         print("Adding test data...")
    #         test_text = "This is a test document for player movement in Godot."
    #         test_vector = model.encode(test_text).tolist()
    #         client.upsert(
    #             collection_name="godot_game",
    #             points=[
    #                 PointStruct(
    #                     id=uuid.uuid4(),
    #                     vector=test_vector,
    #                     payload={"text": test_text, "source": "test_document.txt"}
    #                 )
    #             ]
    #         )
    #         print("Test data added successfully!")
    #     else:
    #         add_test_data()
    #         test_query()
    #     # Now try to query
    #     print("\nQuerying for 'player movement'...")
    #     context = get_context_for_query("How does player movement work?")
    #     print(context)
    #
    # except Exception as e:
    #     print(f"Error: {e}") 
    # # Query for context
    # context = get_context_for_query("How does player movement work?")
    # print(context)
