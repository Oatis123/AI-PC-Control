
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, END
from agent.prompts.main_system_prompt import prompt
from agent.models.polza_ai_models import *
from typing import TypedDict, Annotated
import operator
import logging
from typing import List
from agent.tools.pc_control_tools import *
from agent.tools.web_tools import search_web
from agent.tools.useful_tools import waiting, current_date_time
from agent.tools.screen_tools import get_screenshot_tool
import langchain
import json

langchain.debug = True


tools = [get_installed_software, 
         find_application_name, 
         start_application, 
         get_open_windows,
         scrape_application, 
         interact_with_element_by_rect, 
         execute_bash_command, 
         waiting, 
         current_date_time, 
         get_screenshot_tool, 
         search_web]

tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = grok4_fast.bind_tools(tools)


logging.basicConfig(
    level=logging.INFO,
    filename='agent_logs.txt',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


class AgentState(TypedDict):
    messages: list[BaseMessage]
    ids_to_hide: Annotated[list[str], operator.add]
    screenshot_ids_to_hide: Annotated[list[str], operator.add]
    last_search_web_id: str | None

 
def agent_node(state):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}


def tool_node(state: AgentState) -> dict:
    tools_to_hide = ["scrape_application", "get_installed_software", "get_screenshot_tool"]
    last_message = state["messages"][-1]
    
    is_search_web_called_now = any(
        tc["name"] == "search_web" for tc in last_message.tool_calls
    )
    
    previous_search_web_id = state.get("last_search_web_id")

    is_heavy_tool_called = any(
        tc["name"] in tools_to_hide for tc in last_message.tool_calls
    )

    should_clean_history = is_heavy_tool_called or (is_search_web_called_now and previous_search_web_id)

    previous_ids_to_hide = state.get("ids_to_hide", [])
    screenshot_ids_to_hide = state.get("screenshot_ids_to_hide", [])
    cleaned_messages = []

    if should_clean_history:
        i = 0
        while i < len(state["messages"]):
            msg = state["messages"][i]
            
            if isinstance(msg, ToolMessage):
                should_hide = False
                if msg.tool_call_id in previous_ids_to_hide:
                    should_hide = True
                
                elif is_search_web_called_now and msg.tool_call_id == previous_search_web_id:
                    should_hide = True

                if should_hide:
                    if "Ошибка" in msg.content or "ошибка" in msg.content:
                        cleaned_messages.append(
                            ToolMessage(
                                content=msg.content,
                                tool_call_id=msg.tool_call_id,
                            )
                        )
                    else:
                        cleaned_messages.append(
                            ToolMessage(
                                content="Результат выполнения предыдущего инструмента скрыт для экономии контекста.",
                                tool_call_id=msg.tool_call_id,
                            )
                        )
                    
                    if msg.tool_call_id in screenshot_ids_to_hide:
                        if i + 1 < len(state["messages"]):
                            next_msg = state["messages"][i + 1]
                            if isinstance(next_msg, HumanMessage):
                                content = next_msg.content
                                if isinstance(content, list):
                                    has_image = any(
                                        isinstance(c, dict) and c.get("type") == "image_url"
                                        for c in content
                                    )
                                    if has_image:
                                        i += 1
                else:
                    cleaned_messages.append(msg)
            else:
                 cleaned_messages.append(msg)
            
            i += 1
    else:
        cleaned_messages = state["messages"]

    new_tool_results = []
    current_ids_to_hide = list(previous_ids_to_hide)
    current_screenshot_ids = list(screenshot_ids_to_hide)
    current_search_web_id = None

    for tool_call in last_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        
        if tool_call["name"] == "search_web":
            current_search_web_id = tool_call["id"]

        if tool_call["name"] == "get_screenshot_tool":
            screenshot = tool.invoke(tool_call["args"])
            mime_type = screenshot["mime_type"]
            screenshot_data = screenshot["screenshot_data"]
            
            human_message_content = [
                {"type": "text", "text": "Вот запрошенный скриншот для анализа."},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{screenshot_data}"}}
            ]
            new_tool_results.append(HumanMessage(content=human_message_content))
            
            tool_confirmation = json.dumps({"status": "success", "message": "Image provided in a new message."})
            new_tool_results.append(ToolMessage(content=tool_confirmation, tool_call_id=tool_call["id"]))
            
            current_screenshot_ids.append(tool_call["id"])
        else:
            observation = tool.invoke(tool_call["args"])
            new_tool_results.append(
                ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
            )
        
        if tool_call["name"] in tools_to_hide:
            current_ids_to_hide.append(tool_call["id"])
    
    return {
        "messages": cleaned_messages + new_tool_results,
        "ids_to_hide": current_ids_to_hide,
        "screenshot_ids_to_hide": current_screenshot_ids,
        "last_search_web_id": current_search_web_id,
    }




def should_continue(state):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
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

config = {"recursion_limit": 50}

#for chunk in graph.stream(input_data, stream_mode="values", config=config):
#    print(chunk, end="", flush=True)

def request_to_agent(req: List):
    logging.info(f"Получен новый запрос: {req}")
    
    try:
        input_data = {"messages": [SystemMessage(prompt)] + req}
        logging.info("Данные для графа подготовлены.")
        logging.info("Вызов графа в потоковом режиме...")
        
        final_answer = None
        last_chunk = None 

        for chunk in graph.stream(input_data, config={"recursion_limit": 150}):
            if "__end__" not in chunk:
                logging.info(f"Промежуточный шаг графа: {chunk}")
            
            last_chunk = chunk

            if "__end__" in chunk:
                final_answer = chunk["__end__"]

        logging.info("Граф успешно отработал.")

        if final_answer:
            answer = final_answer.get("messages")
            logging.info("Ответ успешно извлечен из финального узла.")
            logging.info(answer)
            return answer
        elif last_chunk and "agent" in last_chunk:
            agent_messages = last_chunk["agent"].get("messages", [])
            if agent_messages and isinstance(agent_messages[-1], AIMessage):
                answer = [agent_messages[-1]]
                logging.info("Извлечен прямой текстовый ответ от агента.")
                logging.info(answer)
                return answer
        else:
            logging.warning("Граф завершил работу, но не вернул никакого ответа.")
            return None

    except Exception as e:
        logging.error(f"Произошла ошибка при обработке запроса: {req}", exc_info=True)
        raise e