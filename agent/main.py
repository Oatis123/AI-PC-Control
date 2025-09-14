from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage
from prompts.main_system_prompt import prompt
from models.google_models import gemini25_flash, gemini25_flash_lite
from models.ollama_models import qwen3_8b, deepseekr1_8b, cogito_8b, gemma3_4b
from tools.pc_control_tools import *


tools = [get_installed_software, start_application, get_open_windows, scrape_application, interact_with_element_by_rect, execute_bash_command]


agent = create_react_agent(
    model=gemma3_4b,
    tools=tools
)


input_data = {"messages": [SystemMessage(prompt), HumanMessage("Создай папку 123 в корне диска C: и открой её в проводнике.")]}



for chunk in agent.stream(input_data, stream_mode="values"):
    print(chunk, end="", flush=True)