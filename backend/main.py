"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage, config
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .openrouter import get_available_models, query_model
from .version import PRINTNAME, VERSION

app = FastAPI(title=PRINTNAME)

# Add a version endpoint
@app.get("/api/version")
async def get_version():
    return {"printname": PRINTNAME, "version": VERSION}

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
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


class HumanFeedbackRequest(BaseModel):
    """Human feedback for council re-evaluation."""
    feedback: str
    continue_discussion: bool


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    success = storage.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "conversation deleted"}


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
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
    """Get list of available OpenRouter models with current pricing."""
    models = await get_available_models()
    return {"models": models}


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


@app.post("/api/conversations/{conversation_id}/human-feedback")
async def submit_human_feedback(conversation_id: str, request: HumanFeedbackRequest):
    """Submit human chairman feedback and potentially continue discussion."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Add human feedback to conversation
    storage.add_human_feedback(conversation_id, request.feedback, request.continue_discussion)

    if not request.continue_discussion:
        return {"status": "feedback recorded", "continued": False}

    # Rerun council with feedback incorporated
    last_user_message = None
    for msg in reversed(conversation["messages"]):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break

    if not last_user_message:
        raise HTTPException(status_code=400, detail="No user message found to provide feedback on")

    modified_query = f"{last_user_message}\n\nHuman Chairman Feedback: {request.feedback}\n\nPlease reconsider your analysis taking this feedback into account."

    async def event_generator():
        logs_to_send = []
        def sync_log(msg):
            logs_to_send.append(msg)

        try:
            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'log', 'message': '🔄 Starting Revision with Human Feedback...'})}\n\n"
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            
            stage1_results = await stage1_collect_responses(modified_query, log_callback=sync_log)
            for log in logs_to_send:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
            logs_to_send.clear()
            
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(modified_query, stage1_results, log_callback=sync_log)
            for log in logs_to_send:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
            logs_to_send.clear()
            
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(modified_query, stage1_results, stage2_results, log_callback=sync_log)
            for log in logs_to_send:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
            logs_to_send.clear()
            
            # Add assistant message with all stages
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"
            
            # CRITICAL: Re-enable Stage 4 for the next revision
            yield f"data: {json.dumps({'type': 'log', 'message': 'Revision complete. Awaiting further review...'})}\n\n"
            yield f"data: {json.dumps({'type': 'human_input_required'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/conversations/{conversation_id}/end-session")
async def end_session(conversation_id: str, rating: int):
    """End the council session with a rating."""
    if not (0 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    storage.end_session_with_rating(conversation_id, rating)
    return {"status": "session ended", "rating": rating}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        # Helper for logging during stages
        logs_to_send = []
        def sync_log(msg):
            logs_to_send.append(msg)

        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'log', 'message': '🚀 Initializing Council Session...'})}\n\n"
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            yield f"data: {json.dumps({'type': 'log', 'message': 'Stage 1: Querying council members for individual analysis...'})}\n\n"
            
            stage1_results = await stage1_collect_responses(request.content, log_callback=sync_log)
            for log in logs_to_send:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
            logs_to_send.clear()

            print(f"DEBUG SSE: Stage 1 complete with {len(stage1_results)} results")
            yield f"data: {json.dumps({'type': 'log', 'message': f'Stage 1 Complete: Received {len(stage1_results)} responses.'})}\n\n"
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            yield f"data: {json.dumps({'type': 'log', 'message': 'Stage 2: Cross-evaluating responses (Anonymized Peer Ranking)...'})}\n\n"
            
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results, log_callback=sync_log)
            for log in logs_to_send:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
            logs_to_send.clear()

            print(f"DEBUG SSE: Stage 2 complete with {len(stage2_results)} rankings")
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'log', 'message': 'Stage 2 Complete: Peer evaluations and rankings collected.'})}\n\n"
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            yield f"data: {json.dumps({'type': 'log', 'message': 'Stage 3: AI Chairman is synthesizing the final recommendation...'})}\n\n"
            
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results, log_callback=sync_log)
            for log in logs_to_send:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
            logs_to_send.clear()

            print(f"DEBUG SSE: Stage 3 complete")
            yield f"data: {json.dumps({'type': 'log', 'message': 'Stage 3 Complete: Final analysis synthesized.'})}\n\n"
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Human Chairman phase
            yield f"data: {json.dumps({'type': 'log', 'message': 'Stage 4: Awaiting Human Chairman review and feedback...'})}\n\n"
            yield f"data: {json.dumps({'type': 'human_input_required'})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

            # Note: Assistant message will be saved after human feedback is received

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
