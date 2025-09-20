from langchain_ollama import ChatOllama


qwen3_8b = ChatOllama(model="qwen3:8b-q4_K_M")
#deepseekr1_8b = ChatOllama(model="deepseek-r1:8b")
#deepseekr1_7b = ChatOllama(model="deepseek-r1:7b")

#Моделям без reasoning не хватает интелекта для правильного использования инструментов
gemma3_12b = ChatOllama(model="PetrosStav/gemma3-tools:12b")