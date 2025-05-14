"""
main_a2a.py
-----------
Usage:
    python main_a2a.py "תל חי 30 באר שבע"
"""

import sys
import json


from autogen import (
    AssistantAgent,
    UserProxyAgent,
    GroupChat,
    GroupChatManager,
)

import geo_tools          # address_to_plan
import pdf_tools          # plan_to_json + get_plan_pdf
import presentation_tools  # NEW  ← after other imports


# ── Azure OpenAI config (same key you use elsewhere) ───────────────────────────
LLM_CONFIG = {
    "config_list": [
        {
            "model":       "gpt-4o",   # DEPLOYMENT_NAME in Azure
            "api_type":    "azure",
            "api_key":     "EM7HLeBTOHSNHTTPG1mYWUyHyJNZuyXM3VIW01taczzBp4ottOioJQQJ99BEACHYHv6XJ3w3AAAAACOGQ0fz",
            "base_url":    "https://ai-tomgurevich0575ai135301545538.openai.azure.com",
            "api_version": "2025-01-01-preview",
        }
    ],
    "temperature": 0,
}

# ── AssistantAgent (LLM) — calls tools, does NOT execute code ──────────────────
assistant = AssistantAgent(
    name="LLMAgent",
    llm_config=LLM_CONFIG,
    code_execution_config=False,  # never runs Python itself
    system_message=(
        "TOOLS AVAILABLE:\n"
        "• address_to_plan(address_text:str) -> dict  — Parse address into {lat,lon,plans}\n"
        "• plan_to_json(plan_number:str)  -> dict     — Download plan PDF & return Table-5 JSON\n"
        "• json_to_ppt(data:dict)          -> str      — Turn that JSON into a one-slide PowerPoint\n\n"
        "WORKFLOW:\n"
        "1. On any Israeli address ⇒ call address_to_plan.\n"
        "2. Take the first item’s 'Plan' ⇒ call plan_to_json.\n"
        "3. Immediately pass the JSON you receive to json_to_ppt.\n"
        "4. Respond ONLY with the .pptx file path you get back.\n"
        "No commentary, no extra text."
    )

)

# Register tool *signatures* on the LLM agent
assistant.register_for_llm(
    name="address_to_plan",
    description="Parse address → lat/lon + nearby plan numbers",
)(geo_tools.address_to_plan)

assistant.register_for_llm(
    name="plan_to_json",
    description="Download MaVaT PDF & extract Table-5 JSON",
)(pdf_tools.plan_to_json)

# after the two existing assistant.register_for_llm(...) lines
assistant.register_for_llm(
    name="json_to_ppt",
    description="Render the JSON dict as a table image and save it to a one-slide PowerPoint. Returns the PPTX file path.",
)(presentation_tools.json_to_ppt)


slide_agent = UserProxyAgent(
    name="SlideAgent",
    human_input_mode="NEVER",
    code_execution_config={"use_docker": False},
    llm_config=False,
    system_message="I turn JSON dicts into a PowerPoint.",
)
slide_agent.register_for_execution(
    name="json_to_ppt")(presentation_tools.json_to_ppt)


# ── UserProxyAgent — executes BOTH tools, no LLM needed ────────────────────────
exec_agent = UserProxyAgent(
    name="ToolRunner",
    human_input_mode="NEVER",
    code_execution_config={"use_docker": False},
    llm_config=False,            # this agent never calls the LLM
    system_message="I execute tools and return their results.",
)

# Register execution of the same functions
exec_agent.register_for_execution(name="address_to_plan")(geo_tools.address_to_plan)
exec_agent.register_for_execution(name="plan_to_json")(pdf_tools.plan_to_json)

# (Optional) expose get_plan_pdf too in case the LLM ever needs raw PDF bytes
exec_agent.register_for_execution(name="get_plan_pdf")(pdf_tools.TOOL_MAP["get_plan_pdf"])

# ── Termination: stop when final message is a dict or JSON blob ────────────────
def _done(msg):
    # raw dict  OR  JSON string  OR  .pptx path
    if isinstance(msg, dict):
        return True
    txt = getattr(msg, "content", "") or str(msg)
    return txt.strip().startswith("{") or txt.lower().endswith(".pptx")



user_proxy = UserProxyAgent(           # silent proxy to kick things off
    name="User",
    human_input_mode="NEVER",
    code_execution_config=False,
    llm_config=False,
    is_termination_msg=_done,
)

# ── Assemble chat ──────────────────────────────────────────────────────────────
group = GroupChat(
    agents=[user_proxy, assistant, exec_agent, slide_agent],
    messages=[],
    max_round=12,
)
manager = GroupChatManager(groupchat=group, llm_config=LLM_CONFIG)

# ── CLI ------------------------------------------------------------------------
def main(addr: str):
    try:
        # Reset messages before starting
        group.messages = []
        
        # Initiate chat and store the result
        result = user_proxy.initiate_chat(
            manager,
            message=f"Please give me the Table-5 JSON for: {addr}",
        )
        
        # Check if we have any messages
        if not group.messages:
            return {"error": "No response generated"}
            
        # Get the last message
        last = group.messages[-1]
        
        # Return appropriate format
        if isinstance(last, dict):
            return last
        if hasattr(last, 'content'):
            return {"result": last.content}
        return {"result": str(last)}
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('Usage: python main_a2a.py "<address text>"')
    result = main(sys.argv[1])
    if isinstance(result, dict):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)