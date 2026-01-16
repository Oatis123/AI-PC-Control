from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"


deepseek_v31 = ChatOpenAI(
    model="deepseek/deepseek-chat-v3.1",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.9,
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    },
    extra_body={
        "provider": {
            "order": ["fireworks"],
            "allow_fallbacks": False
        }
    }
)

qwen3_235b = ChatOpenAI(
    model="qwen/qwen3-235b-a22b-2507",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    extra_body={
        "provider": {
            "order": ["deepinfra/fp8"],
            "allow_fallbacks": False
        }
    }
)

qwen3_next_80b =ChatOpenAI(
    model="qwen/qwen3-next-80b-a3b-instruct",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    extra_body={
        "provider": {
            "order": ["deepinfra/fp8"],
            "allow_fallbacks": False
        }
    }
)

kimi_k2 = ChatOpenAI(
    model="moonshotai/kimi-k2-0905",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    extra_body={
        "provider": {
            "order": ["parasail/fp8"],
            "allow_fallbacks": False
        }
    }
)

llama4_Scout = ChatOpenAI(
    model="meta-llama/llama-4-scout",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.8,
    extra_body={
        "provider": {
            "order": ["friendli"],
            "allow_fallbacks": True
        }
    },
    default_headers={
        "X-Title": "Data-Sama",

    }
)

grok41_fast = ChatOpenAI(
    model="x-ai/grok-4.1-fast",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    }
)

xaomi_mimo_v2_flash = ChatOpenAI(
    model="xiaomi/mimo-v2-flash:free",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    extra_body={
        "provider": {
            "order": ["xiaomi/fp8"],
            "allow_fallbacks": False
        }
    },
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    }
)

gpt_oss_120b_exacto = ChatOpenAI(
    model="openai/gpt-oss-120b:exacto",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    extra_body={
        "provider": {
            "order": ["deepinfra/fp4"],
            "allow_fallbacks": False
        }
    },
    model_kwargs={
        "reasoning": {
            "effort": "low"
        }
    }
)