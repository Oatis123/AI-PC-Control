from langchain_core.tools import tool
import time
import datetime

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


@tool
def current_date_time():
    '''
    Функция возвращает текущую дату и время в виде отформатированной строки 
    (без секунд и миллисекунд).

    Returns:
        str: Дата и время в формате "ГГГГ-ММ-ДД ЧЧ:ММ"
    '''
    current_time = datetime.datetime.now()
    return current_time.strftime("%Y-%m-%d %H:%M")