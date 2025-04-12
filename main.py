from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import tempfile
import shutil
from pathlib import Path
import json
import re
import sys
# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli import query_database, index_project, index_godot_docs
from qdrant import client

app = FastAPI(title="Godot RAG API")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Add CORS middleware - important for Render deployment where frontend and backend are separate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, change this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define models
class QueryRequest(BaseModel):
    query: str
    limit: int = 3
    collections: List[str] = ["godot_game", "godot_docs"]
    include_rules: bool = False

class IndexProjectRequest(BaseModel):
    project_path: str
    chunk_size: int = 1000
    chunk_overlap: int = 200

class IndexDocsRequest(BaseModel):
    version: str = "stable"
    collection: str = "godot_docs"

class Result(BaseModel):
    source: str
    text: str
    score: float

class CollectionResults(BaseModel):
    collection: str
    results: List[Result]

class QueryResponse(BaseModel):
    query: str
    contexts: List[CollectionResults]

class BaseResponse(BaseModel):
    success: bool
    message: str

class IndexResponse(BaseResponse):
    stats: Dict[str, Any]

class CollectionsResponse(BaseModel):
    success: bool
    collections: List[str]

# Static config for storing paths and configs
config = {
    'project_path': None,
    'rules_file': None
}

# API Routes
@app.post("/api/query", response_model=QueryResponse)
async def api_query(request: QueryRequest):
    try:
        # Call the query_database function from cli.py
        context = query_database(
            text=request.query,
            limit=request.limit,
            collections=request.collections,
            include_rules=request.include_rules
        )
        
        # Parse the results into a structured format
        results = {
            "query": request.query,
            "contexts": []
        }
        
        # Process each collection's results
        current_collection = None
        collection_results = []
        
        # Split by collection sections
        collection_pattern = r"--- CONTEXT FROM ([A-Z_]+) ---"
        collections_sections = re.split(collection_pattern, context)
        
        # First item is likely the prompt, skip it
        if "Prompt:" in collections_sections[0]:
            collections_sections = collections_sections[1:]
        
        # Process the sections
        for i in range(0, len(collections_sections), 2):
            if i+1 >= len(collections_sections):
                break
                
            collection_name = collections_sections[i]
            collection_content = collections_sections[i+1]
            
            # Parse the results in this collection
            source_pattern = r"--- From (.*?) ---\n(.*?)(?=\n--- From|\n\(Relevance score:|\Z)"
            score_pattern = r"\(Relevance score: ([\d.]+)\)"
            
            results_list = []
            
            # Find all source blocks
            source_matches = re.finditer(source_pattern, collection_content, re.DOTALL)
            
            for match in source_matches:
                source = match.group(1)
                text = match.group(2).strip()
                
                # Try to find the score
                score_match = re.search(score_pattern, collection_content)
                score = float(score_match.group(1)) if score_match else 0.5
                
                results_list.append({
                    "source": source,
                    "text": text,
                    "score": score
                })
            
            if results_list:
                results["contexts"].append({
                    "collection": collection_name.lower(),
                    "results": results_list
                })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/index-project", response_model=IndexResponse)
async def api_index_project(request: IndexProjectRequest):
    try:
        # Store the project path for future use
        config['project_path'] = request.project_path
        
        # Call the indexing function
        stats = index_project(
            path=request.project_path, 
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        return {
            "success": True,
            "message": "Project indexed successfully",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-rules", response_model=BaseResponse)
async def api_upload_rules(file: UploadFile = File(...)):
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
            
        # Create a unique filename
        file_path = UPLOAD_DIR / file.filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Store the rules file path
        config['rules_file'] = str(file_path)
        
        # Copy to project_rules.md in the current directory for the CLI tool
        rules_path = Path("project_rules.md")
        shutil.copy(file_path, rules_path)
        
        return {
            "success": True,
            "message": f"Rules file '{file.filename}' uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/index-docs", response_model=IndexResponse)
async def api_index_docs(request: IndexDocsRequest):
    try:
        # Call the indexing function
        stats = index_godot_docs(
            version=request.version,
            collection_name=request.collection
        )
        
        return {
            "success": True,
            "message": "Documentation indexed successfully",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collections", response_model=CollectionsResponse)
async def api_get_collections():
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        return {
            "success": True,
            "collections": collection_names
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Basic health check endpoint for Render
@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable for Render compatibility
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
