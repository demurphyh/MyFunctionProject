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

    words = text.split()
    word_count = len(words)
    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", ""))
    sentence_count = len(re.findall(r'[.!?]+', text)) or 1
    paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
    reading_time_minutes = round(word_count / 200, 1)
    avg_word_length = round(char_count_no_spaces / word_count, 1) if word_count > 0 else 0
    longest_word = max(words, key=len) if words else ""

    analysis_id = str(uuid.uuid4())
    
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

    document = {
        "id": analysis_id,
        "analysis": "text_analysis_record",
        "results": analysis_results,
        "metadata": metadata,
        "originalText": text
    }

    container = get_cosmos_container()
    db_status = "Not Connected"
    
    if container:
        try:
            container.upsert_item(body=document)
            db_status = "Success"
            logging.info(f"Document {analysis_id} saved successfully.")
        except Exception as e:
            db_status = f"Error: {str(e)}"
            logging.error(f"Database upsert failed: {e}")

    response_data = {
        "id": analysis_id,
        "db_status": db_status,
        "analysis": analysis_results, 
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

    limit = req.params.get('limit', 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    container = get_cosmos_container()
    if not container:
        return func.HttpResponse(
            json.dumps({"error": "Database connection failed"}),
            mimetype="application/json",
            status_code=500
        )

    try:
        query = "SELECT * FROM c WHERE c.analysis = 'text_analysis_record' OFFSET 0 LIMIT @limit"
        parameters = [{"name": "@limit", "value": limit}]

        results = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=False 
        ))

        formatted_results = []
        for doc in results:
            formatted_results.append({
                "id": doc.get("id"),
                "analysis": doc.get("results"),
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