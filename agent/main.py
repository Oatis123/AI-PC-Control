from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage
from prompts.main_system_prompt import prompt
from models.google_models import gemini25_flash, gemini25_flash_lite
from models.ollama_models import qwen3_8b, deepseekr1_8b
from tools.pc_control_tools import *


tools = [get_installed_software, find_application_name, start_application, get_open_windows, scrape_application, interact_with_element_by_rect, execute_bash_command]


agent = create_react_agent(
    model=gemini25_flash,
    tools=tools
)


input_data = {"messages": [SystemMessage(prompt), HumanMessage("Посмотри открытое окно Visual Studio Code и оцени открытый код")]}

config = {"recursion_limit": 50}

for chunk in agent.stream(input_data, stream_mode="values", config=config):
    print(chunk, end="", flush=True)