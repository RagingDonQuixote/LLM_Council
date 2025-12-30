"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from . import config


async def stage1_collect_responses(user_query: str, log_callback=None) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        log_callback: Optional callback for logging events

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    current_config = config.get_config()
    council_models = current_config["council_models"]
    personalities = current_config.get("model_personalities", {})
    timeout = current_config.get("response_timeout", 60)

    # Create tasks for all models
    tasks = []
    for model in council_models:
        personality = personalities.get(model, "Expert AI Assistant")
        if log_callback:
            log_callback(f"Preparing query for council member: {model.split('/')[-1]}")
        messages = [
            {"role": "system", "content": f"You are a council member with the following personality: {personality}"},
            {"role": "user", "content": user_query}
        ]
        
        async def query_with_logging(m, msgs, t):
            if log_callback:
                log_callback(f"Waiting for response from: {m.split('/')[-1]}...")
            res = await query_model(m, msgs, timeout=float(t))
            if log_callback:
                if res:
                    log_callback(f"SUCCESS: {m.split('/')[-1]} has responded.")
                else:
                    log_callback(f"FAILED: {m.split('/')[-1]} timed out or error.")
            return res
            
        tasks.append(query_with_logging(model, messages, timeout))

    # Query all models in parallel
    import asyncio
    responses_list = await asyncio.gather(*tasks)
    responses = {model: resp for model, resp in zip(council_models, responses_list)}

    # Format results
    stage1_results = []
    for model, response in zip(council_models, responses_list):
        if response is not None:
            stage1_results.append({
                "model": model,
                "response": response.get('content', ''),
                "usage": response.get('usage', {})
            })
        else:
            # Include a placeholder for failed models so they don't just disappear
            stage1_results.append({
                "model": model,
                "response": "Error: This model failed to respond or timed out.",
                "usage": {"total_tokens": 0},
                "error": True
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    log_callback=None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        log_callback: Optional callback for logging events

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking of ALL {len(stage1_results)} responses.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
Ranking: [Response Letter] > [Response Letter] > [Response Letter] ...

For example, if you think Response B is best, followed by A, then C:
Ranking: Response B > Response A > Response C
"""

    current_config = config.get_config()
    council_models = current_config["council_models"]
    timeout = current_config.get("response_timeout", 60)

    # Create tasks for ranking
    tasks = []
    for model in council_models:
        messages = [
            {"role": "system", "content": "You are a critical judge evaluating multiple AI responses."},
            {"role": "user", "content": ranking_prompt}
        ]
        
        async def query_with_logging(m, msgs, t):
            if log_callback:
                log_callback(f"Judge {m.split('/')[-1]} is evaluating all responses...")
            res = await query_model(m, msgs, timeout=float(t))
            if log_callback:
                if res:
                    log_callback(f"Judge {m.split('/')[-1]} has submitted their ranking.")
                else:
                    log_callback(f"Judge {m.split('/')[-1]} failed to rank.")
            return res
            
        tasks.append(query_with_logging(model, messages, timeout))

    # Query all models in parallel
    import asyncio
    responses_list = await asyncio.gather(*tasks)
    responses = {model: resp for model, resp in zip(council_models, responses_list)}

    # Format results
    stage2_results = []
    for model, response in zip(council_models, responses_list):
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    log_callback=None
) -> Dict[str, Any]:
    """
    Stage 3: A chairman model synthesizes all responses and rankings.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        stage2_results: Results from Stage 2
        log_callback: Optional callback for logging events

    Returns:
        Dict with synthesized response and metadata
    """
    current_config = config.get_config()
    chairman_model = current_config.get("chairman_model", "openai/gpt-4-turbo")
    timeout = current_config.get("response_timeout", 60)

    # Prepare context for chairman
    context = f"User Question: {user_query}\n\n"
    context += "Council Member Responses:\n"
    for result in stage1_results:
        context += f"Model {result['model']}:\n{result['response']}\n\n"

    context += "Peer Evaluations and Rankings:\n"
    for result in stage2_results:
        context += f"Judge {result['model']}:\n{result['ranking']}\n\n"

    system_prompt = """You are the Chairman of the LLM Council. 
Your task is to review all member responses and their peer evaluations.
Synthesize the best points from all responses into one comprehensive, high-quality final answer.
Be objective and acknowledge where models agreed or disagreed if it adds value to the user."""

    if log_callback:
        log_callback(f"Chairman {chairman_model.split('/')[-1]} is reviewing the council's work...")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]

    response = await query_model(chairman_model, messages, timeout=float(timeout))
    
    if log_callback:
        if response:
            log_callback("Chairman has synthesized the final response.")
        else:
            log_callback("Chairman failed to synthesize. System error.")

    return {
        "model": chairman_model,
        "response": response.get('content', '') if response else "Error: Chairman failed to respond.",
        "usage": response.get('usage', {}) if response else {"total_tokens": 0}
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            
            # 1. Try to find "Response X" format
            numbered_matches = re.findall(r'\d+\.\s*Response ([A-Z])', ranking_section)
            if numbered_matches:
                return [f"Response {m}" for m in numbered_matches]
            
            # 2. Try to find just "X" after a number (e.g., "1. A")
            short_matches = re.findall(r'\d+\.\s*([A-Z])(?:\s|$)', ranking_section)
            if short_matches:
                return [f"Response {m}" for m in short_matches]
                
            # 3. Try to find any "Response X" patterns in order
            matches = re.findall(r'Response ([A-Z])', ranking_section)
            if matches:
                return [f"Response {m}" for m in matches]

    # Fallback: try to find any "Response X" patterns anywhere in the text
    matches = re.findall(r'Response ([A-Z])', ranking_text)
    if matches:
        return [f"Response {m}" for m in matches]
        
    # Last resort: find any capital letters A-F that look like they might be rankings
    # (Only if we have a reasonable number of them)
    last_resort = re.findall(r'(?:\d+\.\s*|Ranking:\s*|Best:\s*)([A-F])', ranking_text)
    if last_resort:
        return [f"Response {m}" for m in last_resort]
        
    return []


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.0-flash-001 for title generation (fast and cheap)
    response = await query_model("google/gemini-2.0-flash-001", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Check if we have at least 1 result
    print(f"DEBUG: Stage 1 complete with {len(stage1_results)} results")

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)
    print(f"DEBUG: Stage 2 complete with {len(stage2_results)} rankings")

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    print(f"DEBUG: Starting Stage 3...")
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )
    print(f"DEBUG: Stage 3 complete")

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
