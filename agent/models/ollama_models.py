from langchain_ollama import ChatOllama


qwen3_8b = ChatOllama(model="qwen3:8b-q4_K_M")
deepseekr1_8b = ChatOllama(model="deepseek-r1:8b")

#Моделям без reasoning не хватает интелекта для правильного использования инструментов
#cogito_8b = ChatOllama(model="cogito:8b")
#gemma3_4b = ChatOllama(model="PetrosStav/gemma3-tools:4b")