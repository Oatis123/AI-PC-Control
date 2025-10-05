from langchain.tools import tool
import base64
from PIL import ImageGrab, Image
from io import BytesIO


@tool
def get_screenshot_tool() -> dict:
    """
    Делает скриншот всего экрана и возвращает его в виде строки base64 и MIME-типа.
    Этот инструмент следует использовать, когда нужно увидеть, что в данный момент находится на экране пользователя.
    """
    try:
        screenshot = ImageGrab.grab()
        screenshot.thumbnail((1280, 720), Image.Resampling.LANCZOS)
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=85, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"screenshot_data": img_str, "mime_type": "image/jpeg"}
    except Exception as e:
        return {"error": str(e)}