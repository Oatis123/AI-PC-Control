from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

xiaomi_mimo_v2_flash = ChatOpenAI(
    model="xiaomi/mimo-v2-flash",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.5,
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

gemma4_26b_a4b = ChatOpenAI(
    model="google/gemma-4-26b-a4b-it",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    extra_body={
        "provider": {
            "sort": "latency",
            "allow_fallbacks": True
        }
    }
)

glm_5 = ChatOpenAI(
    model="z-ai/glm-5",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.5,
    extra_body={
        "provider": {
            "sort": "latency",
            "allow_fallbacks": False
        }
    },
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    }
)

llama4_Scout = ChatOpenAI(
    model="meta-llama/llama-4-scout",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.5,
    extra_body={
        "provider": {
            "sort": "latency",
            "allow_fallbacks": False,
            "ignore": ["google-vertex"]
        }
    }
)

kimi_k25 = ChatOpenAI(
    model="moonshotai/kimi-k2.5",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.5,
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    },
    extra_body={
        "provider": {
            "sort": "latency",
            "allow_fallbacks": False
        }
    }
)

deepseek_v32 = ChatOpenAI(
    model="deepseek/deepseek-v3.2",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.5,
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    },
    extra_body={
        "provider": {
            "order": ["friendli"],
            "allow_fallbacks": False
        }
    }
)