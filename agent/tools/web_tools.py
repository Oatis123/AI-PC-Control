from ddgs import DDGS
from langchain_core.tools import tool
from markdownify import markdownify as md


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Ищет информацию в интернете и возвращает список сайтов с описанием.

    Args:
        query (str): Текст поискового запроса.
        num_results (int): Максимальное количество результатов для возврата.

    Returns:
        str: Отформатированная строка с результатами (заголовок, описание, ссылка).
    """
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=num_results)
            
            if not results:
                return "По вашему запросу ничего не найдено."

            formatted_results = []
            for i, res in enumerate(results, 1):
                title = res.get('title', 'Без заголовка')
                body = res.get('body', 'Нет описания')
                url = res.get('href', '#')
                
                formatted_result = (
                    f"### {i}. {title}\n"
                    f"**Краткое описание:** {body}\n"
                    f"**Ссылка:** {url}\n"
                    f"---"
                )
                formatted_results.append(formatted_result)
            
            return "\n".join(formatted_results)
            
    except Exception as e:
        return f"Ошибка при выполнении поиска: {e}"