"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from . import config


async def stage0_analyze_and_plan(user_query: str, log_callback=None) -> Dict[str, Any]:
    """
    Stage 0: Chairman analyzes the task and creates a plan.
    Detects if a multi-step consensus loop is needed.
    """
    current_config = config.get_config()
    chairman_model = current_config.get("chairman_model", "openai/gpt-4-turbo")
    timeout = current_config.get("response_timeout", 60)

    system_prompt = """You are the Strategic Planner of the LLM Council.
Analyze the user's request and determine the best execution strategy.

Identify if the task requires:
1. DIRECT_EXECUTION: A straightforward question or task.
2. CONSENSUS_LOOP: A task where models must first agree on parameters (e.g., "agree on 5 words", "choose a theme", "define a common structure") before proceeding.

Your output must be a JSON object:
{
  "strategy": "DIRECT_EXECUTION" | "CONSENSUS_LOOP",
  "reasoning": "Why this strategy?",
  "current_goal": "What is the immediate next goal for the council members?",
  "requires_consensus": boolean
}
"""

    if log_callback:
        log_callback(f"Chairman {chairman_model.split('/')[-1]} is analyzing the request strategy...")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    import json
    response = await query_model(chairman_model, messages, timeout=float(timeout))
    
    try:
        content = response.get('content', '{}')
        # Clean potential markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        plan = json.loads(content)
        if log_callback:
            log_callback(f"Strategy identified: {plan.get('strategy', 'DIRECT_EXECUTION')}. Goal: {plan.get('current_goal')}")
        return plan
    except Exception as e:
        if log_callback:
            log_callback(f"Error parsing strategy: {str(e)}. Defaulting to DIRECT_EXECUTION.")
        return {
            "strategy": "DIRECT_EXECUTION",
            "reasoning": "Fallback due to parsing error.",
            "current_goal": "Answer the user query.",
            "requires_consensus": False
        }


async def stage1_collect_responses(user_query: str, log_callback=None, instruction=None) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        log_callback: Optional callback for logging events
        instruction: Optional specific instruction from the Chairman's plan
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
        
        system_content = f"You are a council member with the following personality: {personality}."
        if instruction:
            system_content += f"\n\nIMPORTANT CURRENT GOAL: {instruction}"

        messages = [
            {"role": "system", "content": system_content},
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
    plan: Dict[str, Any] = None,
    log_callback=None
) -> Dict[str, Any]:
    """
    Stage 3: A chairman model synthesizes all responses and rankings.
    Can decide to continue the consensus loop if necessary.
    """
    current_config = config.get_config()
    chairman_model = current_config.get("chairman_model", "openai/gpt-4-turbo")
    timeout = current_config.get("response_timeout", 60)

    # Prepare context for chairman
    context = f"Original User Question: {user_query}\n\n"
    if plan:
        context += f"Current Strategic Plan: {plan.get('reasoning')}\n"
        context += f"Current Goal: {plan.get('current_goal')}\n\n"

    context += "Council Member Responses:\n"
    for result in stage1_results:
        context += f"Model {result['model']}:\n{result['response']}\n\n"

    context += "Peer Evaluations and Rankings:\n"
    for result in stage2_results:
        context += f"Judge {result['model']}:\n{result['ranking']}\n\n"

    system_prompt = """You are the Chairman of the LLM Council.
Review the member responses and evaluations.

Your task is to decide:
1. Is the current goal met? (e.g., if a consensus was required, have they agreed?)
2. If YES, synthesize the final high-quality answer.
3. If NO, create a 'Consensus Proposal' or a specific follow-up instruction to resolve the disagreement/lack of parameters.

Your output must be a JSON object:
{
  "action": "FINAL_ANSWER" | "CONTINUE_NEGOTIATION",
  "content": "The synthesized final answer OR the new instruction/proposal for the council",
  "reasoning": "Why are you taking this action?",
  "new_instruction": "If CONTINUE_NEGOTIATION, what exactly should the models do next? (e.g. 'We will use these 5 words: A, B, C, D, E. Now write the poem.')"
}
"""

    if log_callback:
        log_callback(f"Chairman {chairman_model.split('/')[-1]} is evaluating the results and consensus...")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]

    import json
    response = await query_model(chairman_model, messages, timeout=float(timeout))
    
    try:
        raw_content = response.get('content', '{}')
        # Clean potential markdown
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()
        
        decision = json.loads(raw_content)
        
        if log_callback:
            if decision.get('action') == "FINAL_ANSWER":
                log_callback("Chairman has synthesized the final response.")
            else:
                log_callback(f"Chairman requests another round: {decision.get('reasoning')}")

        return {
            "model": chairman_model,
            "action": decision.get('action', 'FINAL_ANSWER'),
            "reasoning": decision.get('reasoning', ''),
            "response": decision.get('content', ''),
            "new_instruction": decision.get('new_instruction', ''),
            "usage": response.get('usage', {}) if response else {"total_tokens": 0}
        }
    except Exception as e:
        if log_callback:
            log_callback(f"Error parsing chairman decision: {str(e)}. Defaulting to FINAL_ANSWER.")
        return {
            "model": chairman_model,
            "action": "FINAL_ANSWER",
            "reasoning": f"Error: {str(e)}",
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
    Run the complete 3-stage council process with consensus loop.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 0: Analysis & Planning
    plan = await stage0_analyze_and_plan(user_query)
    current_instruction = plan.get('current_goal')
    
    max_rounds = 3
    current_round = 1
    last_stage1 = []
    last_stage2 = []
    last_stage3 = {}
    last_metadata = {}

    while current_round <= max_rounds:
        # Stage 1: Collect individual responses
        stage1_results = await stage1_collect_responses(user_query, instruction=current_instruction)
        last_stage1 = stage1_results

        # If no models responded successfully, break
        if not stage1_results:
            break

        # Stage 2: Collect rankings
        stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)
        last_stage2 = stage2_results
        
        # Calculate aggregate rankings
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        last_metadata = {
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate_rankings
        }

        # Stage 3: Synthesize / Decide
        stage3_result = await stage3_synthesize_final(
            user_query,
            stage1_results,
            stage2_results,
            plan=plan
        )
        last_stage3 = stage3_result

        if stage3_result.get('action') == "FINAL_ANSWER" or current_round == max_rounds:
            break
        
        # Prepare for next round
        current_instruction = stage3_result.get('new_instruction', 'Continue the discussion.')
        current_round += 1

    return last_stage1, last_stage2, last_stage3, last_metadata
