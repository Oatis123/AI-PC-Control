from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from prompts.main_system_prompt import prompt
from models.google_models import gemini25_flash, gemini25_flash_lite
from models.ollama_models import qwen3_8b, deepseekr1_8b
from typing import TypedDict, Sequence, Annotated
import operator
from tools.pc_control_tools import *


tools = [get_installed_software, find_application_name, start_application, get_open_windows, scrape_application, interact_with_element_by_rect, execute_bash_command]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = gemini25_flash.bind_tools(tools)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    ids_to_hide: Annotated[list[str], operator.add] 


def agent_node(state):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    ids_to_hide = state.get("ids_to_hide", [])
    if ids_to_hide:
        updated_messages = []
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage) and msg.tool_call_id in ids_to_hide:
                updated_messages.append(
                    ToolMessage(
                        content="Результат выполнения scrape_application скрыт для экономии контекста.",
                        tool_call_id=msg.tool_call_id,
                    )
                )
            else:
                updated_messages.append(msg)
        state["messages"] = updated_messages

    new_tool_results = []
    new_ids_to_hide = []
    
    last_message = state["messages"][-1]

    for tool_call in last_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        new_tool_results.append(
            ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
        )

        if tool_call["name"] == "scrape_application":
            new_ids_to_hide.append(tool_call["id"])
            
    return {"messages": new_tool_results, "ids_to_hide": new_ids_to_hide}


def should_continue(state):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "continue"
    else:
        return "end"


workflow = StateGraph(AgentState)


workflow.add_node("agent", agent_node)
workflow.add_node("action", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)

workflow.add_edge("action", "agent")

graph = workflow.compile()


input_data = {"messages": [SystemMessage(prompt), HumanMessage("Открой мне Firefox и посмотри его содержимое, затем перейди на новую страницу и посмотри её содержимое")]}

config = {"recursion_limit": 50}

for chunk in graph.stream(input_data, stream_mode="values", config=config):
    print(chunk, end="", flush=True)
    