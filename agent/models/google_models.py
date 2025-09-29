from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini25_flash = ChatGoogleGenerativeAI(api_key=GEMINI_API_KEY, model="gemini-2.5-flash") 
gemini25_flash_lite = ChatGoogleGenerativeAI(api_key=GEMINI_API_KEY, model="gemini-2.5-flash-lite")

gemini20_flash = ChatGoogleGenerativeAI(api_key=GEMINI_API_KEY, model="gemini-2.0-flash")
gemini20_flash_lite = ChatGoogleGenerativeAI(api_key=GEMINI_API_KEY, model="gemini-2.0-flash-lite")