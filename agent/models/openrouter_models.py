from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"


nvidia_nemotron_3_super_120b_a12b = ChatOpenAI(
    model="nvidia/nemotron-3-super-120b-a12b",
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

mistral_small_4 = ChatOpenAI(
    model="mistralai/mistral-small-2603",
    api_key=OPENROUTER_API_KEY,
    base_url=BASE_URL,
    temperature=0.5,
    extra_body={
        "provider": {
            "order": ["mistral"],
            "allow_fallbacks": False
        }
    },
    model_kwargs={
        "reasoning": {
            "enabled": True
        }
    }
)

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
            "enabled": True
        }
    }
)