import azure.functions as func
import logging
import json
import re
import os
import uuid
from datetime import datetime, timezone
from azure.cosmos import CosmosClient

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
def get_cosmos_container():
    """Helper to initialize the database connection."""
    # Pulls from local.settings.json (local) or Environment Variables (Azure)
    connection_string = os.environ.get("COSMOS_STRING")
    database_name = os.environ.get("DATABASE_NAME")
    container_name = os.environ.get("CONTAINER_STRING")
    
    if not connection_string:
        logging.error("Cosmos Connection String not found.")
        return None
    
    try:
        client = CosmosClient.from_connection_string(connection_string)
        database = client.get_database_client(database_name)
        return database.get_container_client(container_name)
    except Exception as e:
        logging.error(f"Cosmos DB Initialization Error: {e}")
        return None

# =============================================================================
# FUNCTION APP
# =============================================================================
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="TextAnalyzer")
def TextAnalyzer(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Text Analyzer API was called!')

    # --- STEP 1: GET THE TEXT INPUT ---
    text = req.params.get('text')
    if not text:
        try:
            req_body = req.get_json()
            text = req_body.get('text')
        except:
            pass

    if not text:
        return func.HttpResponse(
            json.dumps({"error": "No text provided"}),
            mimetype="application/json",
            status_code=400
        )

    # --- STEP 2: ANALYZE THE TEXT ---
    words = text.split()
    word_count = len(words)
    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", ""))
    sentence_count = len(re.findall(r'[.!?]+', text)) or 1
    paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
    reading_time_minutes = round(word_count / 200, 1)
    avg_word_length = round(char_count_no_spaces / word_count, 1) if word_count > 0 else 0
    longest_word = max(words, key=len) if words else ""

    # --- STEP 3: PREPARE THE DOCUMENT ---
    analysis_id = str(uuid.uuid4())
    
    # We group the counts here
    analysis_results = {
        "wordCount": word_count,
        "characterCount": char_count,
        "characterCountNoSpaces": char_count_no_spaces,
        "sentenceCount": sentence_count,
        "paragraphCount": paragraph_count,
        "averageWordLength": avg_word_length,
        "longestWord": longest_word,
        "readingTimeMinutes": reading_time_minutes
    }

    metadata = {
        "analyzedAt": datetime.now(timezone.utc).isoformat(),
        "textPreview": text[:100] + "..." if len(text) > 100 else text
    }

    # REQUIRED STRUCTURE:
    # 1. 'id' is mandatory.
    # 2. 'analysis' is your Partition Key (must be a string).
    # 3. 'results' holds the actual math we did.
    document = {
        "id": analysis_id,
        "analysis": "text_analysis_record",
        "results": analysis_results,
        "metadata": metadata,
        "originalText": text
    }

    # --- STEP 4: SAVE TO COSMOS DB ---
    container = get_cosmos_container()
    db_status = "Not Connected"
    
    if container:
        try:
            # We pass the document and explicitly define the partition key
            container.upsert_item(body=document)
            db_status = "Success"
            logging.info(f"Document {analysis_id} saved successfully.")
        except Exception as e:
            db_status = f"Error: {str(e)}"
            logging.error(f"Database upsert failed: {e}")

    # --- STEP 5: RETURN RESPONSE ---
    response_data = {
        "id": analysis_id,
        "db_status": db_status,
        "analysis": analysis_results, # Returning the object to the user as before
        "metadata": metadata
    }

    return func.HttpResponse(
        json.dumps(response_data, indent=2),
        mimetype="application/json",
        status_code=200
    )
    
@app.route(route="GetAnalysisHistory", methods=["GET"])
def GetAnalysisHistory(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('History API was called!')

    # --- STEP 1: GET QUERY PARAMETERS ---
    # Default to 10 if 'limit' isn't provided or isn't a number
    limit = req.params.get('limit', 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    # --- STEP 2: CONNECT TO DATABASE ---
    container = get_cosmos_container()
    if not container:
        return func.HttpResponse(
            json.dumps({"error": "Database connection failed"}),
            mimetype="application/json",
            status_code=500
        )

    try:
        # --- STEP 3: QUERY COSMOS DB ---
        # We query by our Partition Key 'analysis' for efficiency
        # We sort by timestamp (if indexing allows) or just get the latest
        query = "SELECT * FROM c WHERE c.analysis = 'text_analysis_record' OFFSET 0 LIMIT @limit"
        parameters = [{"name": "@limit", "value": limit}]

        # enable_cross_partition_query is False by default, which is good for performance
        results = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=False 
        ))

        # --- STEP 4: FORMAT THE RESPONSE ---
        # We map the internal 'results' field back to 'analysis' for the user
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "id": doc.get("id"),
                "analysis": doc.get("results"), # Mapping back from our stored 'results'
                "metadata": doc.get("metadata")
            })

        response_body = {
            "count": len(formatted_results),
            "results": formatted_results
        }

        return func.HttpResponse(
            json.dumps(response_body, indent=2),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error fetching history: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to retrieve history"}),
            mimetype="application/json",
            status_code=500
        )