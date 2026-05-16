from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

gpt_oss_120b = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.7,
    extra_body={
        "provider": {
            "sort": "latency",
            "allow_fallbacks": True,
            "ignore": ["google-vertex/global"]
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

deepseek_v4_flash = ChatOpenAI(
    model="deepseek/deepseek-v4-flash",
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

nvidia_nemotron_3_super_120b_a12b = ChatOpenAI(
    model="nvidia/nemotron-3-super-120b-a12b",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.8,
    extra_body={
        "provider": {
            "sort": "latency",
            "allow_fallbacks": False,
            "ignore": ["google-vertex/global"]
        }
    },
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    }
)

grok43 = ChatOpenAI(
    model="x-ai/grok-4.3",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.5,
    model_kwargs={
        "reasoning": {
            "enabled": False
        }
    }
)