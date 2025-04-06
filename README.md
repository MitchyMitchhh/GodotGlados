# GodotGlados
Glados has a cli that allows the user to index their godot files and godot documentation to a qdrant vector database. Once the db has those files you can then query the db to gather helpful added context for a LLM to digest.

CLI commands-
    query               Query the vector database
    index-project       Index a Godot project
    index-docs          Index Godot documentation to the RAG system
    create-collection   Create a new collection
    list-collections    List all collections
    delete-collection   Delete a collection

