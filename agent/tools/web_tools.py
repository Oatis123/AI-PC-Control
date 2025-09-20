from ddgs import DDGS
from langchain_core.tools import tool
from markdownify import markdownify as md
import requests
from bs4 import BeautifulSoup


def scrape_webpage(url: str) -> str:
    """
    Вспомогательная функция для загрузки и преобразования одной веб-страницы.
    Возвращает ее содержимое в виде Markdown.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            if element:
                element.decompose()

        content_container = None
        selectors = [
            'article', 'main', '[role="main"]', '.post-content', '.article-body',
            '.content', '#content', '#main', '.article-formatted-body'
        ]
        
        for selector in selectors:
            content_container = soup.select_one(selector)
            if content_container:
                break
        
        if not content_container:
            content_container = soup.body
            if not content_container:
                return f"Не удалось найти контент на странице {url}."
        
        markdown_text = md(str(content_container), heading_style="ATX").strip()

        if not markdown_text:
             return f"Не удалось извлечь контент из найденного блока на странице {url}."

        return markdown_text

    except requests.RequestException as e:
        return f"Ошибка при загрузке страницы {url}: {e}"


@tool
def search_and_scrape(query: str, num_results: int = 3) -> str:
    """
    Инструмент для поиска информации в интернете.
    Принимает поисковый запрос и желаемое количество результатов.
    Возвращает содержимое найденных страниц, преобразованное в Markdown.
    """
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, region='ru-ru', max_results=num_results)
            
            if not results:
                return "По вашему запросу ничего не найдено."

            scraped_contents = []
            for i, res in enumerate(results, 1):
                url = res['href']
                
                content = scrape_webpage(url)
                
                header = f"--- НАЧАЛО КОНТЕНТА ИЗ {url} ---\n\n"
                footer = f"\n\n--- КОНЕЦ КОНТЕНТА ИЗ {url} ---\n\n"
                
                scraped_contents.append(header + content + footer)
            
            return "".join(scraped_contents)
            
    except Exception as e:
        return f"Ошибка при выполнении поиска: {e}"