from langchain_core.tools import tool
import time

@tool
def waiting(sec: int):
    '''
    Приостанавливает выполнение программы на заданное количество секунд.
    Args:
        sec (int): Количество секунд, на которое нужно приостановить выполнение.
    Returns:
        bool: Возвращает True после успешного завершения ожидания.
    '''
    time.sleep(sec)
    return True