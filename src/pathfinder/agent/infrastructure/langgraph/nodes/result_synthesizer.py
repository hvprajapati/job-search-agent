"""Result Synthesizer — formats tool outputs into a user-friendly response."""
from pathfinder.agent.domain.state import SupervisorState


async def result_synthesizer_node(state: SupervisorState) -> dict:
    intent = state.get("intent", "general_question")
    results = state.get("tool_results", {})
    errors = state.get("tool_errors", {})
    profile = state.get("user_profile") or {}
    memory_context = state.get("memory_context", "")

    parts: list[str] = []
    name = profile.get("full_name", "")

    if intent == "search_jobs":
        for _step_id, data in results.items():
            jobs = data.get("jobs", [])
            total = data.get("total", len(jobs))
            if total == 0:
                parts.append("I didn't find any jobs matching your search.")
                if "remote" in memory_context.lower():
                    parts.append(" I know you prefer remote roles — try broadening the location filter?")
                else:
                    parts.append(" Try broadening your criteria?")
            else:
                greeting = f"Hi {name.split()[0]}! " if name else ""
                parts.append(f"{greeting}I found {total} jobs. Here are the top matches:\n")
                for i, job in enumerate(jobs[:5], 1):
                    parts.append(f"**{i}. {job['title']}** at {job.get('company', '')}\n   {job.get('location', '')} | {'Remote' if job.get('remote') == 'remote' else 'Onsite/Hybrid'}\n")

    elif intent == "match_me":
        has_score = False
        for _step_id, data in results.items():
            if "overall_score" in data:
                score = data["overall_score"]
                parts.append(f"Your match score is **{score}/100**.\n")
                if data.get("strengths"):
                    parts.append("**Strengths:**\n")
                    for s in data["strengths"][:3]:
                        parts.append(f"  ✅ {s}\n")
                if data.get("skill_gaps"):
                    parts.append("\n**Skill gaps:**\n")
                    for g in data["skill_gaps"][:3]:
                        parts.append(f"  📋 {g['skill']} ({g['severity']})\n")
                has_score = True
            elif "recommendations" in data:
                recs = data["recommendations"]
                if recs:
                    parts.append(f"I found **{len(recs)}** jobs that might be a good fit:\n")
                    for i, r in enumerate(recs[:5], 1):
                        parts.append(f"**{i}. {r['title']}** at {r.get('company', 'Unknown')}\n")
                    parts.append("\nTo see how well you match a specific job, tell me which one interests you.")
                else:
                    parts.append("I couldn't find any matching jobs right now. Try updating your profile with more skills.")
        if not has_score and not parts:
            parts.append("Let me find jobs that match your profile. What kind of role are you looking for?")

    elif intent == "general_question":
        if name:
            parts.append(f"Hi {name.split()[0]}! ")
        skills_list = [s["name"] for s in profile.get("skills", [])[:5]]
        if skills_list:
            parts.append(f"I see your skills include {', '.join(skills_list)}. ")
        parts.append("I can help you find jobs, check your match for specific roles, or tailor your resume. What would you like to do?")
    else:
        parts.append(f"I've processed your {intent} request.")

    if errors:
        parts.append("\n\n*Note: Some steps encountered issues:*")
        for step_id, error in list(errors.items())[:2]:
            parts.append(f"\n- {step_id}: {error[:150]}")

    return {"final_response": "\n".join(parts) if parts else "I've completed your request. Is there anything else I can help with?", "agent_phase": "response_synthesized"}
