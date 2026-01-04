"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import os
import asyncio
from datetime import datetime

from . import storage, config, models_service, audit_service
from .council import (
    run_full_council, 
    generate_conversation_title, 
    stage0_analyze_and_plan,
    stage1_collect_responses, 
    stage2_collect_rankings, 
    stage3_synthesize_final, 
    calculate_aggregate_rankings
)
from .openrouter import query_model
from .version import PRINTNAME, VERSION

app = FastAPI(title=PRINTNAME)

# Add a version endpoint
@app.get("/api/version")
async def get_version():
    return {"printname": PRINTNAME, "version": VERSION}

# Enable CORS for local development
# ToBeDeleted_start
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# ToBeDeleted_end

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, this should be specific
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


class CouncilConfig(BaseModel):
    """Configuration for the LLM Council."""
    council_models: List[str]
    chairman_model: str
    model_personalities: Dict[str, str]
    substitute_models: Dict[str, str] = {}
    consensus_strategy: str = "borda"
    response_timeout: int = 60


class HumanFeedbackRequest(BaseModel):
    """Human feedback for council re-evaluation."""
    feedback: str
    continue_discussion: bool


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/audit/{conversation_id}")
async def get_audit_logs(conversation_id: str):
    logs = storage.storage.get_audit_logs(conversation_id)
    return logs

class AnalysisRequest(BaseModel):
    analysis: str

@app.post("/api/audit/{conversation_id}/analysis")
async def save_analysis(conversation_id: str, request: AnalysisRequest):
    storage.storage.add_analysis_result(conversation_id, request.analysis)
    return {"status": "success"}

@app.post("/api/audit/{conversation_id}/export")
async def export_audit(conversation_id: str):
    try:
        archive_path = audit_service.export_audit_archive(conversation_id)
        return {"status": "success", "archive_path": archive_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: str):
    """Archive a conversation."""
    success = storage.storage.archive_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success"}

@app.delete("/api/conversations/{conversation_id}/permanent")
async def delete_conversation_permanent(conversation_id: str):
    """Delete a conversation permanently."""
    success = storage.storage.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "id": conversation_id}

@app.post("/api/conversations/{conversation_id}/reset")
async def reset_conversation(conversation_id: str):
    """Reset a conversation (clear messages and state)."""
    success = storage.storage.reset_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "id": conversation_id}

@app.get("/api/fail-lists")
async def get_fail_lists():
    """Get all fail lists."""
    return storage.storage.get_fail_lists()

@app.post("/api/fail-lists/{id}/activate")
async def activate_fail_list(id: int):
    """Set a fail list as active."""
    storage.storage.set_active_fail_list(id)
    return {"status": "success"}

@app.post("/api/models/test-availability")
async def test_models_availability(model_ids: List[str]):
    """Test availability of a list of models in parallel."""
    from .openrouter import query_model
    from datetime import datetime
    
    async def test_one(model_id):
        try:
            # Simple ping with a very short timeout
            resp = await query_model(model_id, [{"role": "user", "content": "ping"}], timeout=15)
            return model_id, resp is not None
        except:
            return model_id, False

    # Parallel testing
    results = await asyncio.gather(*[test_one(mid) for mid in model_ids])
    failed_models = [mid for mid, ok in results if not ok]
    
    # Save the result as a new fail list
    name = f"Test {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    storage.storage.save_fail_list(name, failed_models)
    
    return {
        "failed_models": failed_models, 
        "total_tested": len(model_ids),
        "failed_count": len(failed_models)
    }

# Unified Models API Endpoints
@app.get("/api/unified-models/base")
async def get_base_models(search: str = None, limit: int = 1000):
    """Get list of unique base models with optional search."""
    from .unified_model_service import unified_model_service
    
    base_models = unified_model_service.get_base_models()
    
    # Apply search if provided
    if search and search.strip():
        # Filter base models by search query
        search_lower = search.lower()
        filtered_base_models = []
        for base_model in base_models:
            # Search in base model name and developer
            if (search_lower in base_model['base_model_name'].lower() or 
                search_lower in base_model['developer_id'].lower() or
                search_lower in base_model['print_name_part1'].lower()):
                filtered_base_models.append(base_model)
        base_models = filtered_base_models
    
    # Limit results
    return base_models[:limit]

@app.get("/api/unified-models/variants/{base_model_id}")
async def get_model_variants(base_model_id: str):
    """Get all variants for a specific base model."""
    from .unified_model_service import unified_model_service
    
    variants = unified_model_service.get_variants_for_base_model(base_model_id)
    return variants

@app.get("/api/unified-models/search")
async def search_models(q: str, limit: int = 20):
    """Global search across all unified models."""
    from .unified_model_service import unified_model_service
    
    results = unified_model_service.search_models(q, limit)
    return results

@app.get("/api/unified-models/all")
async def get_all_unified_models():
    """Get ALL unified models for the Data Inspector."""
    from .unified_model_service import unified_model_service
    return unified_model_service.get_all_unified_models()

@app.post("/api/unified-models/refresh")
async def refresh_unified_models():
    """Trigger refresh of all models from providers."""
    from .unified_model_service import unified_model_service
    
    try:
        count = await unified_model_service.refresh_all_models()
        return {"status": "success", "models_refreshed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh models: {str(e)}")

@app.get("/api/unified-models/statistics")
async def get_model_statistics():
    """Get statistics about unified model database."""
    from .unified_model_service import unified_model_service
    
    stats = unified_model_service.get_model_statistics()
    return stats

@app.post("/api/unified-models/update-latencies")
async def update_model_latencies():
    """Update latency data for all models."""
    from .unified_model_service import unified_model_service
    
    try:
        await unified_model_service.update_latencies()
        return {"status": "success", "message": "Latency update completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update latencies: {str(e)}")

@app.post("/api/unified-models/test-latency/{model_id}")
async def test_unified_model_latency(model_id: int):
    """Perform a live latency check for a specific unified model."""
    from .unified_model_service import unified_model_service
    import httpx
    import time
    from datetime import datetime
    
    # Get the model from DB to get its provider ID
    conn = storage.storage.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM unified_models WHERE id = ?", (model_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model = dict(row)
    provider_data = json.loads(model['provider_raw_data'])
    or_id = provider_data.get('id')
    
    if not or_id:
        raise HTTPException(status_code=400, detail="No provider ID for live check")
    
    # Simple live check (e.g., HEAD request to provider or specific endpoint)
    # For OpenRouter, we could try to fetch its specific metadata again
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # We just do a ping or small request
            await client.get("https://openrouter.ai/api/v1/models")
        
        latency_live = (time.time() - start_time) * 1000
        timestamp = datetime.utcnow().isoformat()
        
        # Update DB
        conn = storage.storage.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE unified_models 
            SET latency_live = ?, latency_live_timestamp = ? 
            WHERE id = ?
        ''', (latency_live, timestamp, model_id))
        conn.commit()
        conn.close()
        
        return {"status": "success", "latency_live": latency_live, "timestamp": timestamp}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.storage.create_conversation(conversation_id)
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    success = storage.storage.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "conversation deleted"}


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/api/config", response_model=CouncilConfig)
async def get_config():
    """Get current council configuration."""
    return config.get_config()


@app.put("/api/config")
async def update_config(request: CouncilConfig):
    """Update council configuration."""
    config.update_config(request.dict())
    return {"status": "configuration updated"}


@app.get("/api/available-models")
async def get_available_models_endpoint():
    """Get list of available OpenRouter models with current pricing, filtered by active fail list."""
    models = await models_service.models_service.fetch_model_metadata()
    
    # Filter by active fail list
    failed_models = storage.storage.get_active_fail_list()
    if failed_models:
        models = [m for m in models if m["id"] not in failed_models]
        
    return {"models": models}

@app.get("/api/templates")
async def list_templates():
    """List all task templates."""
    return storage.storage.list_templates()

@app.post("/api/templates")
async def save_template(template: Dict[str, Any]):
    """Save or update a template."""
    storage.storage.save_template(template)
    return {"status": "template saved"}

@app.get("/api/boards")
async def list_boards():
    """List all AI boards."""
    return storage.storage.list_boards()

@app.post("/api/boards")
async def save_board(board: Dict[str, Any]):
    """Save or update an AI board."""
    storage.storage.save_board(board)
    return {"status": "board saved"}

@app.delete("/api/boards/{board_id}")
async def delete_board(board_id: str):
    """Delete an AI board."""
    storage.storage.delete_board(board_id)
    return {"status": "board deleted"}

@app.get("/api/prompts")
async def list_prompts():
    """List all prompts."""
    return storage.storage.list_prompts()

@app.post("/api/prompts")
async def save_prompt(prompt: Dict[str, Any]):
    """Save or update a prompt."""
    storage.storage.save_prompt(prompt)
    return {"status": "prompt saved"}

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt."""
    storage.storage.delete_prompt(prompt_id)
    return {"status": "prompt deleted"}

@app.post("/api/prompts/{prompt_id}/use")
async def track_prompt_usage(prompt_id: str):
    """Increment usage count for a prompt."""
    storage.storage.track_prompt_usage(prompt_id)
    return {"status": "usage tracked"}

@app.get("/api/test-latency/{model_id:path}")
async def test_model_latency(model_id: str, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Test the latency of a specific model."""
    import time
    print(f"DEBUG: Testing latency for model: {model_id} with provided key: {'Yes' if x_api_key else 'No'}")
    start_time = time.time()
    
    # Simple test message
    messages = [{"role": "user", "content": "Hello, respond with only one word: 'Ready'"}]
    
    # Use a short timeout for the test
    try:
        response = await query_model(model_id, messages, timeout=15.0, api_key=x_api_key)
    except Exception as e:
        print(f"DEBUG: Error during latency test for {model_id}: {e}")
        response = None
    
    end_time = time.time()
    latency = end_time - start_time
    
    if response is None:
        print(f"DEBUG: Latency test FAILED for {model_id}")
        return {"status": "error", "model": model_id, "latency": latency, "message": "Model failed to respond"}
        
    print(f"DEBUG: Latency test SUCCESS for {model_id}: {latency:.2f}s")
    return {"status": "ok", "model": model_id, "latency": round(latency, 2), "response": response.get('content')}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the council process using the Blueprint orchestrator.
    Returns a streaming response with logs, stage results, and session state.
    """
    # Check if conversation exists
    conversation = storage.storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Determine role based on session status
    session_state = storage.storage.get_session_state(conversation_id)
    role = "human_chairman" if session_state and session_state.get("status") == "paused" else "user"

    # Add user message
    storage.storage.add_user_message(conversation_id, request.content, role=role)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.storage.update_conversation_title(conversation_id, title)

    async def event_generator():
        logs_to_send = []
        def sync_log(msg):
            print(f"[COUNCIL] {msg}")
            logs_to_send.append(msg)

        try:
            # Run the council process via the orchestrator
            stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
                request.content,
                conversation_id=conversation_id,
                log_callback=sync_log
            )

            # Send logs collected during execution
            for log in logs_to_send:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
            
            # Send current session state (blueprint, task index, status)
            session_state = storage.storage.get_session_state(conversation_id)
            if session_state:
                yield f"data: {json.dumps({'type': 'session_state', 'data': session_state})}\n\n"

            # Send stage results
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': metadata})}\n\n"
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Add assistant message to history
            storage.storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                metadata
            )

            # Handle Breakpoints
            if session_state and session_state.get("status") == "paused":
                yield f"data: {json.dumps({'type': 'human_input_required', 'reason': 'breakpoint'})}\n\n"

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/conversations/{conversation_id}/human-feedback")
async def submit_human_feedback(conversation_id: str, request: HumanFeedbackRequest):
    """
    Submit human chairman feedback. If continue_discussion is True, 
    it triggers the council to proceed to the next task or reconsider.
    """
    print(f"[FEEDBACK] Received for {conversation_id}: {request.feedback}")
    conversation = storage.storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Add human feedback to conversation
    storage.storage.add_human_feedback(conversation_id, request.feedback, request.continue_discussion)

    if not request.continue_discussion:
        return {"status": "feedback recorded", "continued": False}

    # If continuing, we use the same streaming logic as send_message
    return await send_message(conversation_id, SendMessageRequest(content=f"Feedback from Chairman: {request.feedback}"))


class RatingRequest(BaseModel):
    """Request for ending a session with a rating."""
    rating: int


@app.post("/api/conversations/{conversation_id}/end-session")
async def end_session(conversation_id: str, request: RatingRequest):
    """End the council session with a rating."""
    if not (0 <= request.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

    conversation = storage.storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    storage.storage.end_session_with_rating(conversation_id, request.rating)
    return {"status": "session ended", "rating": request.rating}

# API Keys Endpoints

class ApiKeyRequest(BaseModel):
    provider: str
    key_value: str
    description: str = ""
    limit_amount: Optional[float] = None
    limit_reset: Optional[str] = None
    is_active: bool = True

@app.get("/api/keys")
async def list_api_keys():
    """List all API keys."""
    return storage.storage.list_api_keys()

@app.post("/api/keys")
async def save_api_key(request: ApiKeyRequest):
    """Save a new API key."""
    # Generate label: first 5 ... last 5
    key_val = request.key_value
    if len(key_val) > 10:
        label = f"{key_val[:5]}...{key_val[-5:]}"
    else:
        label = key_val
        
    key_data = {
        "provider": request.provider,
        "key_value": request.key_value,
        "label": label,
        "description": request.description,
        "limit_amount": request.limit_amount,
        "limit_reset": request.limit_reset,
        "is_active": request.is_active
    }
    
    # Auto-check OpenRouter limit if applicable
    if request.provider == "openrouter":
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {request.key_value}"})
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    key_data["limit_amount"] = data.get("limit")
                    key_data["limit_remaining"] = data.get("limit_remaining")
                    key_data["usage_amount"] = data.get("usage")
                    key_data["limit_reset"] = data.get("limit_reset")
        except Exception as e:
            print(f"Failed to check OpenRouter key: {e}")

    new_id = storage.storage.save_api_key(key_data)
    return {"status": "success", "id": new_id, "data": key_data}

@app.put("/api/keys/{key_id}")
async def update_api_key(key_id: int, request: ApiKeyRequest):
    """Update an existing API key."""
    existing = storage.storage.get_api_key(key_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Key not found")
        
    # Keep existing stats unless refreshed
    key_data = dict(existing)
    key_data.update({
        "provider": request.provider,
        "key_value": request.key_value,
        "description": request.description,
        "limit_amount": request.limit_amount,
        "limit_reset": request.limit_reset,
        "is_active": request.is_active
    })
    
    # Update label if key changed
    if request.key_value != existing["key_value"]:
        key_val = request.key_value
        if len(key_val) > 10:
            key_data["label"] = f"{key_val[:5]}...{key_val[-5:]}"
        else:
            key_data["label"] = key_val

    storage.storage.save_api_key(key_data)
    return {"status": "success", "id": key_id}

@app.delete("/api/keys/{key_id}")
async def delete_api_key(key_id: int):
    """Delete an API key."""
    storage.storage.delete_api_key(key_id)
    return {"status": "success"}

@app.post("/api/keys/{key_id}/check")
async def check_api_key(key_id: int):
    """Check/Refresh an API key's status (OpenRouter only for now)."""
    key = storage.storage.get_api_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
        
    if key["provider"] == "openrouter":
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key['key_value']}"})
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    key["limit_amount"] = data.get("limit")
                    key["limit_remaining"] = data.get("limit_remaining")
                    key["usage_amount"] = data.get("usage")
                    key["limit_reset"] = data.get("limit_reset")
                    key["last_checked"] = datetime.utcnow().isoformat()
                    storage.storage.save_api_key(key)
                    return {"status": "success", "data": key}
                else:
                    return {"status": "error", "message": f"API returned {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    return {"status": "skipped", "message": "Provider not supported for auto-check"}


# DB Admin Endpoints
@app.get("/api/admin/db/tables")
async def list_db_tables():
    """List all tables in the database."""
    conn = storage.storage.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Add virtual tables
    if os.path.exists("backend/all_models_dump.json"):
        tables.append("RAW_OPENROUTER_DUMP")
        
    return {"tables": tables}

@app.get("/api/admin/db/table/{table_name}")
async def get_table_content(
    table_name: str, 
    page: int = 1, 
    page_size: int = 50,
    filter_column: Optional[str] = None,
    filter_value: Optional[str] = None
):
    """Get content of a table with pagination and optional filtering."""
    
    # Handle Virtual Table: RAW_OPENROUTER_DUMP
    if table_name == "RAW_OPENROUTER_DUMP":
        if not os.path.exists("backend/all_models_dump.json"):
             raise HTTPException(status_code=404, detail="Dump file not found")
             
        try:
            with open("backend/all_models_dump.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Flatten/Stringify complex fields for display
            processed_data = []
            for item in data:
                processed_item = {}
                for k, v in item.items():
                    if isinstance(v, (dict, list)):
                        processed_item[k] = json.dumps(v)
                    else:
                        processed_item[k] = v
                processed_data.append(processed_item)
                
            # Filter
            if filter_column and filter_value is not None:
                # Case-insensitive partial match
                filtered = []
                for item in processed_data:
                    val = str(item.get(filter_column, ""))
                    if filter_value.lower() in val.lower():
                        filtered.append(item)
                processed_data = filtered
            
            # Pagination
            total_count = len(processed_data)
            offset = (page - 1) * page_size
            end = offset + page_size
            page_data = processed_data[offset:end]
            
            return {
                "data": page_data,
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading dump file: {str(e)}")

    # Regular SQLite Tables
    conn = storage.storage.get_db_connection()
    cursor = conn.cursor()
    
    # Safety check: ensure table exists to prevent injection via table_name
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Table not found")
        
    # Prepare filter
    where_clause = ""
    filter_params = []
    
    if filter_column and filter_value is not None:
        # Validate column name to prevent injection
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        if filter_column not in columns:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Column '{filter_column}' not found")
            
        where_clause = f"WHERE {filter_column} LIKE ?"
        filter_params = [f"%{filter_value}%"]

    # Get Data
    offset = (page - 1) * page_size
    query = f"SELECT * FROM {table_name} {where_clause} LIMIT ? OFFSET ?"
    params = filter_params + [page_size, offset]
    
    cursor.execute(query, tuple(params))
    rows = [dict(row) for row in cursor.fetchall()]
    
    # Get Count
    count_query = f"SELECT COUNT(*) FROM {table_name} {where_clause}"
    cursor.execute(count_query, tuple(filter_params))
    total_count = cursor.fetchone()[0]
    
    conn.close()
    return {
        "data": rows,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1
    }

@app.post("/api/admin/db/sql")
async def execute_sql_query(query: dict):
    """Execute a raw SQL SELECT query."""
    sql = query.get("sql", "").strip()
    if not sql.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
        
    conn = storage.storage.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"data": rows, "count": len(rows)}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
