"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

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
    return {"status": "success"}

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
async def test_model_latency(model_id: str):
    """Test the latency of a specific model."""
    import time
    print(f"DEBUG: Testing latency for model: {model_id}")
    start_time = time.time()
    
    # Simple test message
    messages = [{"role": "user", "content": "Hello, respond with only one word: 'Ready'"}]
    
    # Use a short timeout for the test
    try:
        response = await query_model(model_id, messages, timeout=15.0)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
