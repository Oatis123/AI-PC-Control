from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

POLZA_AI_API_KEY = os.getenv("POLZA_AI_API_KEY")
BASE_URL = "https://api.polza.ai/api/v1"


#DeepSeek Models
deepseek_v31 = ChatOpenAI(
    model="deepseek/deepseek-v3.1-terminus",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

#Googles models
gemini20_flash = ChatOpenAI(
    model="google/gemini-2.0-flash-001",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

gemini25_flash_lite = ChatOpenAI(
    model="google/gemini-2.5-flash-lite",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

gemini25_flash = ChatOpenAI(
    model="google/gemini-2.5-flash",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

#OpenAI models
gpt_oss_120b = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

gpt5_mini = ChatOpenAI(
    model="openai/gpt-5-mini",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

gpt5_nano = ChatOpenAI(
    model="openai/gpt-5-nano",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

gpt_o4_mini = ChatOpenAI(
    model="openai/o4-mini",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

#Meta models
llama4_maverick = ChatOpenAI(
    model="meta-llama/llama-4-maverick",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

#Qwen models
qwen3_vl = ChatOpenAI(
    model="qwen/qwen3-vl-235b-a22b-thinking",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

#Cohere models
command_r = ChatOpenAI(
    model="cohere/command-r-08-2024",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

#xAI models
grok4_fast = ChatOpenAI(
    model="x-ai/grok-4.1-fast",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)

#Anthropic
claude_haiku_45 = ChatOpenAI(
    model="anthropic/claude-haiku-4.5",
    api_key=POLZA_AI_API_KEY,
    base_url=BASE_URL,
)