from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer 
import os
from dotenv import load_dotenv
import uuid

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

# Create a collection for your Godot game files
# Only run this once when setting up
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
# Example usage
if __name__ == "__main__":
    # First time setup
    # create_collection()
    
    # Index some files
    # index_file("player.gd")
    # index_file("game_rules.md")
    print("Testing Qdrant connection...")
    
    try:
        # Check collections
        collections = client.get_collections()
        print(f"Connected successfully! Available collections: {collections}")
        
        # Check if godot_game exists
        collection_names = [c.name for c in collections.collections]
        if "godot_game" not in collection_names:
            print("Collection 'godot_game' doesn't exist. Creating it now...")
            
            # Create the collection
            client.create_collection(
                collection_name="godot_game",
                vectors_config=VectorParams(
                    size=model.get_sentence_embedding_dimension(),
                    distance=Distance.COSINE
                )
            )
            print("Collection created successfully!")
            
            # Add some test data if you want
            print("Adding test data...")
            test_text = "This is a test document for player movement in Godot."
            test_vector = model.encode(test_text).tolist()
            client.upsert(
                collection_name="godot_game",
                points=[
                    PointStruct(
                        id=uuid.uuid4(),
                        vector=test_vector,
                        payload={"text": test_text, "source": "test_document.txt"}
                    )
                ]
            )
            print("Test data added successfully!")
        else:
            add_test_data()
            test_query()
        # Now try to query
        print("\nQuerying for 'player movement'...")
        context = get_context_for_query("How does player movement work?")
        print(context)
        
    except Exception as e:
        print(f"Error: {e}") 
    # Query for context
    context = get_context_for_query("How does player movement work?")
    print(context)
