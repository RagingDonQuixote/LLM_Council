"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from . import config


async def stage0_analyze_and_plan(user_query: str, log_callback=None, conversation_id: str = None) -> Dict[str, Any]:
    """
    Stage 0: Chairman analyzes the task and creates a Mission Blueprint.
    Creates a task list (event tree) with optimal resource allocation.
    """
    current_config = config.get_config()
    # ToBeDeleted_start
    # chairman_model = current_config.get("chairman_model", "openai/gpt-4-turbo")
    # ToBeDeleted_end
    chairman_model = current_config.get("chairman_model")
    if not chairman_model:
        raise ValueError("Chairman model not configured")
    timeout = current_config.get("response_timeout", 60)

    system_prompt = """You are the Strategic Planner of the LLM Council.
Analyze the user's request and create a Mission Blueprint (Event Tree).

Your task is to break down the request into logical steps (Tasks).
For each task, identify:
1. The goal and specific instructions.
2. The optimal model types/skills needed (e.g., creative, technical, analytical, vision).
3. If the task requires a COUNCIL_CONSENSUS (multiple models) or a SINGLE_SPECIALIST.
4. If a human BREAKPOINT is needed (user must approve or provide input).

Your output must be a JSON object. Do not include any introductory or concluding text. Use only valid JSON.
{
  "mission_name": "A short descriptive name",
  "reasoning": "Overall strategy explanation",
  "blueprint": {
    "tasks": [
      {
        "id": "t1",
        "label": "Brief label",
        "type": "COUNCIL_CONSENSUS" | "SINGLE_SPECIALIST" | "CHAIRMAN_DECISION",
        "description": "Detailed instructions for this step",
        "required_skills": ["skill1", "skill2"],
        "depends_on": [],
        "breakpoint": boolean
      }
    ]
  }
}
"""

    if log_callback:
        log_callback(f"Chairman {chairman_model.split('/')[-1]} is designing the mission blueprint...")

    from .storage import storage
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    import json
    response = await query_model(chairman_model, messages, timeout=float(timeout))
    
    # Audit log for planning
    if conversation_id:
        storage.add_audit_log(
            conversation_id, 
            step="stage0_plan", 
            model_id=chairman_model, 
            log_message="Chairman generated the mission blueprint.",
            raw_data=response
        )

    if response is None:
        raise ValueError(f"Chairman model {chairman_model} failed to respond (likely rate limited or API error).")

    try:
        content = response.get('content', '{}')
        # Clean potential markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            # Check if it's really a code block or just a mention
            blocks = content.split("```")
            if len(blocks) >= 3:
                content = blocks[1].strip()
            else:
                content = content.strip()
        
        # Fallback: if content starts with { and ends with }, but contains extra text
        if not content.startswith("{") and "{" in content:
            content = "{" + content.split("{", 1)[1]
        if not content.endswith("}") and "}" in content:
            content = content.rsplit("}", 1)[0] + "}"
            
        # Robust JSON cleaning: use strict=False to handle control characters
        # If there are still issues, we can add more targeted cleaning.
        plan = json.loads(content, strict=False)
        if log_callback:
            # ToBeDeleted_start
            # log_callback(f"Strategy identified: {plan.get('strategy', 'DIRECT_EXECUTION')}. Goal: {plan.get('current_goal')}")
            # ToBeDeleted_end
            strategy = plan.get('strategy')
            goal = plan.get('current_goal')
            if strategy and goal:
                log_callback(f"Strategy identified: {strategy}. Goal: {goal}")
            else:
                log_callback("Strategy identified, but some fields are missing in blueprint.")
        return plan
    except Exception as e:
        if log_callback:
            log_callback(f"Error parsing strategy: {str(e)}. Raw response: {content}")
        raise ValueError(f"Failed to parse Mission Blueprint: {str(e)}")


async def route_models_by_skills(required_skills: List[str], available_models: List[str]) -> List[str]:
    """
    Select models from available_models that best match the required_skills.
    If no models match perfectly, returns the original council_models.
    """
    if not required_skills:
        return available_models

    from .models_service import models_service
    metadata_list = await models_service.fetch_model_metadata()
    metadata_map = {m['id']: m for m in metadata_list}

    scored_models = []
    for model_id in available_models:
        meta = metadata_map.get(model_id, {})
        description = meta.get('description', '').lower()
        name = meta.get('name', '').lower()
        tags = [t.lower() for t in meta.get('tags', [])]
        
        score = 0
        for skill in required_skills:
            skill = skill.lower()
            if skill in description or skill in name or skill in tags:
                score += 1
            # Add specific capability checks
            if skill == 'vision' and meta.get('capabilities', {}).get('vision'):
                score += 2
            if skill == 'reasoning' and meta.get('capabilities', {}).get('thinking'):
                score += 2
        
        scored_models.append((model_id, score))

    # Sort by score descending
    scored_models.sort(key=lambda x: x[1], reverse=True)
    
    # Return top matches (at least 3 if possible for consensus, or top 1 for specialist)
    # For now, let's just return those with score > 0, or all if none scored.
    matches = [m[0] for m in scored_models if m[1] > 0]
    return matches if matches else available_models


async def query_with_substitute(model: str, messages: List[Dict[str, Any]], timeout: float, substitutes: Dict[str, str], log_callback=None) -> Any:
    """Query a model and fall back to a substitute if it fails."""
    if log_callback:
        log_callback(f"Waiting for response from: {model.split('/')[-1]}...")
        
    res = await query_model(model, messages, timeout=timeout)
    
    if res is None and substitutes and model in substitutes:
        sub = substitutes[model]
        if sub and sub != model:
            if log_callback:
                log_callback(f"⚠️ Model {model.split('/')[-1]} failed. Switching to substitute {sub.split('/')[-1]}...")
            res = await query_model(sub, messages, timeout=timeout)
            if res:
                res["is_substitute"] = True
                res["original_model"] = model

    if log_callback:
        if res:
            log_callback(f"SUCCESS: {model.split('/')[-1]} has responded.")
        else:
            log_callback(f"FAILED: {model.split('/')[-1]} timed out or error.")
    return res


async def stage1_collect_responses(user_query: str, log_callback=None, instruction=None, target_models=None, human_feedback=None, conversation_id: str = None, task_id: str = None) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models or specific target models.
    """
    from .storage import storage
    current_config = config.get_config()
    council_models = target_models if target_models else current_config["council_models"]
    personalities = current_config.get("model_personalities", {})
    substitutes = current_config.get("substitute_models", {})
    timeout = current_config.get("response_timeout", 60)

    # Create tasks for all models
    tasks = []
    for model in council_models:
        # ToBeDeleted_start
        # personality = personalities.get(model, "Expert AI Assistant")
        # ToBeDeleted_end
        personality = personalities.get(model)
        if not personality:
             # ToBeDeleted_start
             # personality = "Expert AI Assistant (Default)"
             # ToBeDeleted_end
             personality = "Council Member"
             
        if log_callback:
            log_callback(f"Preparing query for council member: {model.split('/')[-1]}")
        
        system_content = f"You are a council member with the following personality: {personality}."
        if instruction:
            system_content += f"\n\nIMPORTANT CURRENT GOAL: {instruction}"
        
        if human_feedback:
            system_content += f"\n\nCONTEXT FROM HUMAN CHAIR:\n{human_feedback}"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_query}
        ]
        
        tasks.append(query_with_substitute(model, messages, float(timeout), substitutes, log_callback))

    # Query all models in parallel
    import asyncio
    responses_list = await asyncio.gather(*tasks)
    responses = {model: resp for model, resp in zip(council_models, responses_list)}

    # Format results
    stage1_results = []
    for model, response in zip(council_models, responses_list):
        # Audit log for each individual response
        if conversation_id:
            storage.add_audit_log(
                conversation_id,
                step="stage1_query",
                task_id=task_id,
                model_id=model,
                log_message=f"Model {model.split('/')[-1]} provided an individual response.",
                raw_data=response
            )
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
    log_callback=None,
    conversation_id: str = None,
    task_id: str = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        log_callback: Optional callback for logging events
        conversation_id: Optional conversation ID for auditing
        task_id: Optional task ID for auditing

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
    substitutes = current_config.get("substitute_models", {})
    timeout = current_config.get("response_timeout", 60)

    # Create tasks for ranking
    tasks = []
    for model in council_models:
        messages = [
            {"role": "system", "content": "You are a critical judge evaluating multiple AI responses."},
            {"role": "user", "content": ranking_prompt}
        ]
        
        tasks.append(query_with_substitute(model, messages, float(timeout), substitutes, log_callback))

    # Query all models in parallel
    import asyncio
    responses_list = await asyncio.gather(*tasks)
    responses = {model: resp for model, resp in zip(council_models, responses_list)}

    # Format results
    stage2_results = []
    from .storage import storage
    for model, response in zip(council_models, responses_list):
        # Audit log for each ranking
        if conversation_id:
            storage.add_audit_log(
                conversation_id,
                step="stage2_ranking",
                task_id=task_id,
                model_id=model,
                log_message=f"Judge {model.split('/')[-1]} provided peer evaluations and rankings.",
                raw_data=response
            )

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
    log_callback=None,
    human_feedback=None,
    conversation_id: str = None,
    task_id: str = None
) -> Dict[str, Any]:
    """
    Stage 3: A chairman model synthesizes all responses and rankings.
    Can decide to continue the consensus loop if necessary.
    """
    current_config = config.get_config()
    chairman_model = current_config.get("chairman_model")
    substitutes = current_config.get("substitute_models", {})
    if not chairman_model:
        raise ValueError("Chairman model not configured in settings.")
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

CRITICAL INSTRUCTION:
Prioritize quantitative data and specific numerical facts (e.g., stock prices, P/E ratios, revenue figures) over purely narrative or qualitative descriptions. 
If one model provides specific figures and another provides only a general description, ensure the final synthesis incorporates the specific figures.
Do not sacrifice precision for 'flow' or 'style'.

CONSENSUS REFINEMENT:
If the peer evaluations show disagreement (e.g., Model A ranks Model B low, and vice versa), act as an arbiter.
Identify the root cause of disagreement (e.g., factual error vs. stylistic preference).
If the disagreement is factual, verify who provided sources or more specific data.
If the disagreement is stylistic, synthesize the best structure from both.

Your task is to decide:
1. Is the current goal met? (e.g., if a consensus was required, have they agreed?)
2. Is the user's ORIGINAL request completely fulfilled? (e.g., if the user asked for a poem after the consensus, is the poem there?)
3. If BOTH are YES, synthesize the final high-quality answer.
4. If NO to either, create a 'Consensus Proposal' or a specific follow-up instruction to resolve the disagreement OR move to the next part of the task.

IMPORTANT: Do not finalize (FINAL_ANSWER) if a multi-step task is only partially complete. If the council has agreed on parameters (like 5 words) but hasn't performed the main task (like writing the poem), set action to 'CONTINUE_NEGOTIATION' and instruct them to perform the main task using the agreed parameters.

Your output must be a JSON object:
{
  "action": "FINAL_ANSWER" | "CONTINUE_NEGOTIATION",
  "content": "The synthesized final answer OR the new instruction/proposal for the council",
  "reasoning": "Why are you taking this action? Explain if the goal is met and if the user's full request is addressed.",
  "new_instruction": "If CONTINUE_NEGOTIATION, what exactly should the models do next? (e.g. 'We have agreed on these 5 words: A, B, C, D, E. Now, each member must write the erotic love poem as requested.')"
}
"""

    if log_callback:
        log_callback(f"Chairman {chairman_model.split('/')[-1]} is evaluating the results and consensus...")

    if human_feedback:
        system_prompt += f"\n\nCONTEXT FROM HUMAN CHAIR:\n{human_feedback}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]

    import json
    response = await query_with_substitute(chairman_model, messages, float(timeout), substitutes, log_callback)
    
    # Audit log for synthesis
    if conversation_id:
        from .storage import storage
        storage.add_audit_log(
            conversation_id,
            step="stage3_synthesis",
            task_id=task_id,
            model_id=chairman_model,
            log_message="Chairman evaluated the results and consensus.",
            raw_data=response
        )

    if response is None:
        raise ValueError(f"Chairman model {chairman_model} failed to respond (likely rate limited or API error).")

    try:
        raw_content = response.get('content', '{}')
        # Clean potential markdown
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()
        
        decision = json.loads(raw_content, strict=False)
        
        if log_callback:
            # ToBeDeleted_start
            # if decision.get('action') == "FINAL_ANSWER":
            # ToBeDeleted_end
            action = decision.get('action')
            if action == "FINAL_ANSWER":
                log_callback("Chairman has synthesized the final response.")
            elif action == "CONTINUE_NEGOTIATION":
                log_callback(f"Chairman requests another round: {decision.get('reasoning')}")
            else:
                log_callback(f"Chairman returned unknown action: {action}")

        return {
            "model": chairman_model,
            "action": decision.get('action'),
            "reasoning": decision.get('reasoning', ''),
            "response": decision.get('content', ''),
            "new_instruction": decision.get('new_instruction', ''),
            "usage": response.get('usage', {}) if response else {"total_tokens": 0}
        }
    except Exception as e:
        if log_callback:
            log_callback(f"Error parsing chairman decision: {str(e)}.")
        # ToBeDeleted_start
        # return {
        #     "model": chairman_model,
        #     "action": "FINAL_ANSWER",
        #     "reasoning": f"Error: {str(e)}",
        #     "response": response.get('content', '') if response else "Error: Chairman failed to respond.",
        #     "usage": response.get('usage', {}) if response else {"total_tokens": 0}
        # }
        # ToBeDeleted_end
        raise ValueError(f"Chairman decision parsing failed: {str(e)}")


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


from .strategies import get_strategy

# ToBeDeleted_start
# def calculate_aggregate_rankings(
#     stage2_results: List[Dict[str, Any]],
#     label_to_model: Dict[str, str],
#     strategy_name: str = "borda"
# ) -> List[Dict[str, Any]]:
# ToBeDeleted_end

def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    strategy_name: str
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models using a specific strategy.
    """
    # Parse rankings for all entries first
    for ranking in stage2_results:
        if "parsed_ranking" not in ranking:
            ranking["parsed_ranking"] = parse_ranking_from_text(ranking['ranking'])
            
    from .strategies import get_strategy
    strategy = get_strategy(strategy_name)
    return strategy.calculate(stage2_results, label_to_model)


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

    current_config = config.get_config()
    title_model = current_config.get("chairman_model")
    if not title_model:
        # ToBeDeleted_start
        # return "New Conversation (No Chairman)"
        # ToBeDeleted_end
        return "Unbenannte Mission"
    
    response = await query_model(title_model, messages, timeout=30.0)

    if response is None:
        # ToBeDeleted_start
        # return "New Conversation"
        # ToBeDeleted_end
        return "Unbenannte Mission"

    # ToBeDeleted_start
    # title = response.get('content', 'New Conversation').strip()
    # ToBeDeleted_end
    title = response.get('content', 'Unbenannte Mission').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str, conversation_id: str = None, log_callback=None) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete council process based on the Mission Blueprint.
    """
    from .storage import storage
    
    # Try to load existing session state
    session_state = storage.get_session_state(conversation_id) if conversation_id else None
    
    # Heuristic for reset - improved slightly
    is_reset = any(word in user_query.lower() for word in ["reset", "neustart", "verwerfen"]) and \
               any(word in user_query.lower() for word in ["mission", "blueprint", "projekt", "plan"])
    
    # Handle paused state (Breakpoint)
    if session_state and session_state.get("status") == "paused" and not is_reset:
        if log_callback:
            log_callback("Human Chair has provided input or approval. Resuming mission...")
        
        # Simple approval detection
        is_approval = any(word in user_query.lower() for word in ["approve", "proceed", "continue", "weiter", "ok", "abgenickt", "genehmigt"])
        
        if not is_approval:
            # User provided feedback, add it to human feedback context
            session_state["human_feedback"] = session_state.get("human_feedback", "") + "\nHuman Chair Feedback: " + user_query
        
        session_state["status"] = "in_progress"
        if conversation_id:
            storage.update_session_state(conversation_id, session_state)

    if not session_state or is_reset:
        # Stage 0: Analysis & Planning
        if log_callback:
            log_callback("Chairman is designing a new Mission Blueprint..." if is_reset else "Chairman is designing the Mission Blueprint...")
        
        plan = await stage0_analyze_and_plan(user_query, log_callback=log_callback, conversation_id=conversation_id)
        
        # ToBeDeleted_start
        # session_state = {
        #     "mission_name": plan.get("mission_name", "Mission"),
        #     "blueprint": plan.get("blueprint", {"tasks": []}),
        #     "current_task_index": 0,
        #     "results": {},
        #     "status": "in_progress"
        # }
        # ToBeDeleted_end
        
        mission_name = plan.get("mission_name")
        blueprint = plan.get("blueprint")
        
        if not mission_name:
            # ToBeDeleted_start
            # mission_name = "Unnamed Mission"
            # ToBeDeleted_end
            mission_name = "Unbenannte Mission"
        if not blueprint or "tasks" not in blueprint:
            raise ValueError("Mission Blueprint is missing tasks.")

        session_state = {
            "mission_name": mission_name,
            "blueprint": blueprint,
            "current_task_index": 0,
            "results": {},
            "status": "in_progress"
        }
        if conversation_id:
            storage.update_session_state(conversation_id, session_state)
    
    blueprint = session_state.get("blueprint", {"tasks": []})
    tasks = blueprint.get("tasks", [])
    
    current_config = config.get_config()
    all_council_models = current_config["council_models"]
    
    last_stage1 = []
    last_stage2 = []
    last_stage3 = {}
    last_metadata = {}

    while session_state["current_task_index"] < len(tasks):
        idx = session_state["current_task_index"]
        task = tasks[idx]
        
        if log_callback:
            # ToBeDeleted_start
            # log_callback(f"🚀 Executing Task {idx+1}/{len(tasks)}: {task.get('label')}")
            # ToBeDeleted_end
            task_label = task.get('label', f'Task {idx+1}')
            log_callback(f"🚀 Executing {task_label}...")
            log_callback(f"Context: {task.get('description', 'No description provided.')}")

        # Skill-based routing
        required_skills = task.get("required_skills", [])
        target_models = await route_models_by_skills(required_skills, all_council_models)
        
        if log_callback:
            log_callback(f"Selected experts: {[m.split('/')[-1] for m in target_models]}")

        # Execute task based on type
        task_type = task.get("type")
        if not task_type:
            raise ValueError(f"Task {idx+1} is missing a 'type' field.")
        
        if task_type == "COUNCIL_CONSENSUS":
            # Run Stage 1: Collect responses
            stage1_results = await stage1_collect_responses(
                user_query, 
                log_callback=log_callback, 
                instruction=task.get("description"),
                target_models=target_models,
                human_feedback=session_state.get("human_feedback"),
                conversation_id=conversation_id,
                task_id=task.get("id")
            )
            last_stage1 = stage1_results

            # Run Stage 2: Collect rankings
            stage2_results, label_to_model = await stage2_collect_rankings(
                user_query, 
                stage1_results,
                log_callback=log_callback,
                conversation_id=conversation_id,
                task_id=task.get("id")
            )
            last_stage2 = stage2_results
            
            consensus_strategy = current_config.get("consensus_strategy")
            if not consensus_strategy:
                raise ValueError("Consensus strategy not configured in settings.")

            # Calculate aggregate rankings
            aggregate_rankings = calculate_aggregate_rankings(
                stage2_results,
                label_to_model,
                consensus_strategy
            )
            last_metadata = {
                "label_to_model": label_to_model,
                "aggregate_rankings": aggregate_rankings,
                "task_id": task.get("id")
            }

            # Run Stage 3: Synthesize
            stage3_result = await stage3_synthesize_final(
                user_query,
                stage1_results,
                stage2_results,
                plan={"current_goal": task.get("description")},
                log_callback=log_callback,
                human_feedback=session_state.get("human_feedback"),
                conversation_id=conversation_id,
                task_id=task.get("id")
            )
            last_stage3 = stage3_result
            
        elif task_type == "SINGLE_SPECIALIST":
            # Run only Stage 1 with the top expert
            specialist = [target_models[0]]
            stage1_results = await stage1_collect_responses(
                user_query, 
                log_callback=log_callback, 
                instruction=task.get("description"),
                target_models=specialist,
                human_feedback=session_state.get("human_feedback"),
                conversation_id=conversation_id,
                task_id=task.get("id")
            )
            last_stage1 = stage1_results
            # ToBeDeleted_start
            # last_stage3 = {
            #     "action": "FINAL_ANSWER",
            #     "response": stage1_results[0].get("response", ""),
            #     "reasoning": f"Specialist {specialist[0].split('/')[-1]} completed the task."
            # }
            # ToBeDeleted_end
            
            response_content = stage1_results[0].get("response") if stage1_results else None
            if not response_content:
                response_content = "Error: Specialist failed to provide a response."
                
            last_stage3 = {
                "action": "FINAL_ANSWER",
                "response": response_content,
                "reasoning": f"Specialist {specialist[0].split('/')[-1]} completed the task."
            }
            last_metadata = {"task_id": task.get("id"), "specialist": specialist[0]}

        # Save result for this task in session state
        session_state["results"][task.get("id")] = last_stage3.get("response")
        session_state["current_task_index"] += 1
        
        if conversation_id:
            storage.update_session_state(conversation_id, session_state)

        # Check for breakpoint
        if task.get("breakpoint"):
            if log_callback:
                log_callback(f"🛑 Breakpoint reached at task '{task.get('label')}'. Awaiting user approval.")
            session_state["status"] = "paused"
            if conversation_id:
                storage.update_session_state(conversation_id, session_state)
            break

    # If all tasks finished
    if session_state["current_task_index"] >= len(tasks):
        session_state["status"] = "completed"
        if conversation_id:
            storage.update_session_state(conversation_id, session_state)
            
            # Export to markdown if we have a final answer
            final_ans = last_stage3.get("response") or last_stage3.get("content")
            if final_ans:
                try:
                    filepath = storage.export_to_markdown(conversation_id, final_ans, user_query)
                    if log_callback:
                        log_callback(f"📄 Result exported to {filepath}")
                except Exception as e:
                    if log_callback:
                        log_callback(f"⚠️ Failed to export markdown: {str(e)}")

    return last_stage1, last_stage2, last_stage3, last_metadata
