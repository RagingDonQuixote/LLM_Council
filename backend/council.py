"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from . import config


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

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
        messages = [
            {"role": "system", "content": f"You are a council member with the following personality: {personality}"},
            {"role": "user", "content": user_query}
        ]
        tasks.append(query_model(model, messages, timeout=float(timeout)))

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
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

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
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- You MUST rank EVERY SINGLE response provided above (from A to {labels[-1]}) - do not skip any!
- Do not add any other text or explanations in the ranking section

Example of the correct format for your FINAL RANKING section (if there are 3 responses):

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking of ALL {len(stage1_results)} responses:"""

    messages_base = [{"role": "user", "content": ranking_prompt}]

    current_config = config.get_config()
    council_models = current_config["council_models"]
    personalities = current_config.get("model_personalities", {})

    # Create tasks for all models
    tasks = []
    for model in council_models:
        personality = personalities.get(model, "Expert AI Assistant")
        messages = [
            {"role": "system", "content": f"You are a council member with the following personality: {personality}. Your task is to rank the responses of your peers."},
            {"role": "user", "content": ranking_prompt}
        ]
        tasks.append(query_model(model, messages))

    # Get rankings from all council models in parallel
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
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    current_config = config.get_config()
    chairman_model = current_config["chairman_model"]

    # Query the chairman model
    response = await query_model(chairman_model, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": chairman_model,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": chairman_model,
        "response": response.get('content', '')
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
