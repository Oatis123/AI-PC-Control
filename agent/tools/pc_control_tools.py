import subprocess
import winreg
import shlex
import psutil
import time
from typing import List, Dict, Any, Union, Optional

from langchain_core.tools import tool
from pywinauto import Desktop
from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError
from playwright.sync_api import sync_playwright, Page
from comtypes.gen.UIAutomationClient import UIA_TogglePatternId, UIA_SelectionItemPatternId, ToggleState_Off, ToggleState_On, ToggleState_Indeterminate


def _get_installed_software():
    all_apps = set()

    command_classic = r'''
    Get-ItemProperty HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*, 
                     HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*, 
                     HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | 
    Where-Object {$_.PSObject.Properties['DisplayName'] -and $_.DisplayName -ne $null} |
    Select-Object -ExpandProperty DisplayName
    '''
    
    result_classic = subprocess.run(["powershell", "-Command", command_classic], capture_output=True, text=True, encoding='utf-8', errors='ignore')

    if result_classic.returncode == 0:
        classic_apps = {line.strip() for line in result_classic.stdout.splitlines() if line.strip()}
        all_apps.update(classic_apps)

    command_modern = r'Get-AppxPackage | Select-Object -ExpandProperty Name'
    result_modern = subprocess.run(["powershell", "-Command", command_modern], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    if result_modern.returncode == 0:
        modern_apps = {line.strip() for line in result_modern.stdout.splitlines() if line.strip()}
        all_apps.update(modern_apps)

    full_list = sorted(list(all_apps))
    
    stop_words = [
        'sdk', 'driver', 'redistributable', 'runtime', 'update', 
        'package', 'microsoft .net', 'visual c++', 'prerequisites',
        'manifest', 'host', 'tools', 'amd', 'nvidia', 'intel', 
        'microsoft.windows', 'microsoft.vclibs', 'microsoft.ui',
        'microsoft.web', 'microsoft.aspnet', 'microsoft.testplatform',
        'vs_', 'windows sdk', 'debugger', 'targeting', 'interop'
    ]

    filtered_list = [
        app for app in full_list 
        if not any(stop_word.lower() in app.lower() for stop_word in stop_words)
    ]
    
    return filtered_list


@tool
def get_installed_software():
    """Возвращает отфильтрованный список названий установленных на компьютере программ.
    Функция объединяет классические (Win32) и современные (UWP) приложения,
    убирая из списка системные компоненты, драйверы и библиотеки, чтобы предоставить
    только релевантные для пользователя программы. Не принимает аргументов."""

    return _get_installed_software()



@tool
def find_application_name(approximate_name: str) -> str:
    """
    Находит точное название установленного приложения по его примерному названию.
    
    Эта функция получает полный список установленных программ и ищет в нём первое
    наиболее подходящее совпадение. Идеально подходит для получения корректного 
    имени перед использованием инструмента `start_application`.

    Args:
        approximate_name (str): Приблизительное, неполное или нечувствительное 
                                к регистру имя приложения для поиска (например, 
                                "chrome", "photoshop").

    Returns:
        str: Полное, точное имя найденного приложения (например, "Google Chrome") 
             или сообщение об ошибке, если ничего не найдено.
    """
    all_apps = _get_installed_software()
    
    search_term = approximate_name.lower()
    
    for app_name in all_apps:
        if search_term in app_name.lower():
            return app_name
    
    return f"Ошибка: Приложение '{approximate_name}' не найдено среди установленных программ."


def _get_classic_app_paths():
    app_paths = {}
    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]

    for hkey in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
        for path in registry_paths:
            try:
                key = winreg.OpenKey(hkey, path, 0, winreg.KEY_READ)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        display_name, install_location, display_icon = None, None, None
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        except OSError:
                            pass
                        try:
                            display_icon = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                        except OSError:
                            pass
                        try:
                            install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                        except OSError:
                            pass
                        
                        executable_path = None
                        if display_icon:
                            executable_path = display_icon.split(',')[0].strip('"')
                        elif install_location:
                            executable_path = install_location.strip('"')

                        if display_name and executable_path:
                            app_paths[display_name.lower()] = executable_path
            except FileNotFoundError:
                pass
    return app_paths


def _start_application_by_name(app_name: str) -> bool:
    app_name_lower = app_name.lower()

    try:
        classic_app_map = _get_classic_app_paths()
        for name, path in classic_app_map.items():
            if app_name_lower in name:
                subprocess.Popen(shlex.split(f'"{path}"'))
                time.sleep(2.0)
                return True
    except Exception as e:
        print(f"Ошибка при поиске в реестре: {e}")

    try:
        command = f'Get-AppxPackage | Where-Object {{$_.Name -like "*{app_name}*"}} | Select-Object -First 1 -ExpandProperty PackageFamilyName'
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0 and result.stdout.strip():
            package_family_name = result.stdout.strip()
            launch_command = f'explorer.exe shell:appsFolder\\{package_family_name}!App'
            subprocess.Popen(launch_command, shell=True)
            time.sleep(2.0)
            return True
    except Exception as e:
        print(f"Ошибка при поиске современных приложений: {e}")

    try:
        simple_name = app_name_lower.split(' ')[0]
        subprocess.Popen(f'start {simple_name}', shell=True)
        time.sleep(2.0)
        return True
    except Exception as e:
        print(f"Простой запуск не удался: {e}")

    print(f"Не удалось найти и запустить приложение: '{app_name}'")
    return False


@tool
def start_application(app_name: str)->bool:
    """Запускает приложение на компьютере по его названию.
    В качестве `app_name` следует передавать одно из названий, полученных от инструмента
    `get_installed_software`. Инструмент использует несколько методов для поиска
    и запуска программы. Возвращает True в случае успеха и False в случае неудачи."""
        
    return _start_application_by_name(app_name=app_name)


@tool
def get_open_windows():
    """Возвращает список всех открытых сейчас приложений."""
    desktop = Desktop(backend="uia")
    windows = desktop.windows()
    window_titles = [win.window_text() for win in windows if win.window_text()]
    
    if not window_titles:
        return "не найдено открытых окон"
    
    return "\n".join(window_titles)


def _start_app_with_playwright(app_name: str, port: int = 9222) -> Optional[subprocess.Popen]:
    app_name_lower = app_name.lower()
    classic_app_map = _get_classic_app_paths()
    executable_path = None
    for name, path in classic_app_map.items():
        if app_name_lower in name:
            executable_path = path
            break
    
    if not executable_path:
        return None
        
    command = f'"{executable_path}" --remote-debugging-port={port}'
    proc = subprocess.Popen(shlex.split(command))
    time.sleep(3.0)
    return proc


def _scrape_pywinauto_element(element: Any, results_list: List[Dict[str, Any]]):
    try:
        element_info = {
            "name": element.element_info.name,
            "class_name": element.element_info.class_name,
            "control_type": element.element_info.control_type,
            "rectangle": str(element.element_info.rectangle),
            "is_visible": element.is_visible(),
            "is_enabled": element.is_enabled(),
        }
        results_list.append(element_info)

        for child in element.children():
            _scrape_pywinauto_element(child, results_list)
    except Exception:
        pass


#def _scrape_playwright_page(page: Page) -> List[Dict[str, Any]]:
#    ui_elements = []
#    all_locators = page.locator('*')
#    
#    for i in range(all_locators.count()):
#        try:
#            element = all_locators.nth(i)
#            element_info = {
#                "tag_name": element.evaluate('node => node.tagName.toLowerCase()'),
#                "id": element.get_attribute('id'),
#                "class": element.get_attribute('class'),
#                "text_content": element.text_content(timeout=500),
#                "bounding_box": element.bounding_box(),
#                "is_visible": element.is_visible(),
#                "is_enabled": element.is_enabled()
#            }
#            ui_elements.append(element_info)
#        except Exception:
#            pass
#            
#    return ui_elements


@tool
def scrape_application(name: str) -> Union[List[Dict[str, Any]], str]:
    """
    Возвращает отфильтрованный и оптимизированный список интерактивных UI-элементов,
    включая их состояние (включен/выбран).

    Эта функция сканирует окно приложения, извлекая свойства только тех элементов,
    с которыми можно взаимодействовать. Она игнорирует фоновые панели и контейнеры.
    Структура возвращаемых данных оптимизирована для экономии контекста LLM.

    Args:
        name (str): Часть заголовка окна приложения для поиска.

    Returns:
        Union[List[Dict[str, Any]], str]:
            - Список словарей, где каждый словарь представляет интерактивный UI-элемент.
            - Строка с сообщением об ошибке.
    """
    try:
        desktop = Desktop(backend="uia")
        main_win_spec = desktop.window(title_re=f".*{name}.*", found_index=0)

        if not main_win_spec.exists(timeout=20):
            return f"Ошибка: Окно с именем, содержащим '{name}', не найдено."

        main_win = main_win_spec.wrapper_object()

        if not main_win.is_active():
            main_win.set_focus()
            main_win_spec.wait('active', timeout=20)

        all_elements = main_win.descendants()
        element_details = []

        non_interactive_types = {
            'Pane', 'Group', 'Separator', 'ToolBar', 'ScrollBar', 'Image'
        }

        # Словарь для более понятного представления состояний
        toggle_state_map = {
            ToggleState_Off: 'Off',
            ToggleState_On: 'On',
            ToggleState_Indeterminate: 'Indeterminate'
        }

        for element in all_elements:
            try:
                if not element.is_visible():
                    continue

                element_info = element.element_info
                control_type = element_info.control_type
                name_prop = element_info.name
                text_prop = element.window_text()

                if control_type in non_interactive_types:
                    continue

                if control_type == 'Custom' and not name_prop and not text_prop:
                    continue

                # --- ОПТИМИЗИРОВАННЫЙ СЛОВАРЬ DETAILS ---
                details = {
                    "name": name_prop,
                    "text": text_prop,
                    "control_type": control_type,
                    "is_enabled": element.is_enabled(),
                    "rectangle": {
                        "left": element.rectangle().left,
                        "top": element.rectangle().top,
                        "right": element.rectangle().right,
                        "bottom": element.rectangle().bottom,
                    }
                }

                ## 1. Проверяем состояние для чекбоксов и переключателей
                #if element.is_pattern_supported(UIA_TogglePatternId):
                #    toggle_pattern = element.get_pattern(UIA_TogglePatternId)
                #    state = toggle_pattern.CurrentToggleState
                #    details["toggle_state"] = toggle_state_map.get(state, "Unknown")

                ## 2. Проверяем состояние для радиокнопок и элементов списка
                #if element.is_pattern_supported(UIA_SelectionItemPatternId):
                #    selection_pattern = element.get_pattern(UIA_SelectionItemPatternId)
                #    details["is_selected"] = selection_pattern.CurrentIsSelected

                element_details.append(details)

            except Exception as e:
                print(f"Скрытая ошибка при обработке элемента: {e}") # Добавить для отладки
                continue
        return element_details

    except ElementNotFoundError:
        return f"Произошла ошибка: Окно с именем '{name}' не найдено после ожидания."
    except Exception as e:
        return f"Произошла непредвиденная ошибка при работе с '{name}': {e}"
    

@tool
def interact_with_element_by_rect(
    name: str,
    rectangle: Dict[str, int],
    action: str,
    text_to_set: Optional[str] = None
) -> Union[str, Any]:
    """
    Находит UI-элемент по его координатам (rectangle) и выполняет над ним действие.
    Перед взаимодействием активирует окно, если оно неактивно.

    Args:
        name (str): Часть заголовка окна приложения для поиска.
        rectangle (Dict[str, int]): Словарь с координатами элемента.
                                      Должен содержать ключи: 'left', 'top', 'right', 'bottom'.
        action (str): Действие для выполнения. Поддерживаемые действия:
                      'click', 'double_click', 'right_click', 'set_text', 'get_text', 'press_enter',
                      'scroll_up', 'scroll_down', 'scroll_left', 'scroll_right',
                      'zoom_in', 'zoom_out'.
        text_to_set (Optional[str]): Текст для ввода (обязателен для действия 'set_text').

    Returns:
        Union[str, Any]:
            - Строка с сообщением об успехе или ошибке.
            - Результат действия (например, текст элемента для 'get_text').
    """
    try:
        desktop = Desktop(backend="uia")
        main_win_spec = desktop.window(title_re=f".*{name}.*", found_index=0)

        if not main_win_spec.exists(timeout=20):
            return f"Ошибка: Окно с именем '{name}' не найдено."

        main_win = main_win_spec.wrapper_object()
        
        if not main_win.is_active():
            main_win.set_focus()
            main_win_spec.wait('active', timeout=20)

        target_element = None
        for element in main_win.descendants():
            try:
                if not element.is_visible():
                    continue

                elem_rect = element.rectangle()
                if (elem_rect.left == rectangle['left'] and
                    elem_rect.top == rectangle['top'] and
                    elem_rect.right == rectangle['right'] and
                    elem_rect.bottom == rectangle['bottom']):
                    
                    target_element = element
                    break
            except Exception:
                continue

        if not target_element:
            # Для зума не требуется конкретный элемент, достаточно окна
            if 'zoom' not in action:
                 return f"Ошибка: Элемент с координатами {rectangle} не найден."

        action = action.lower()
        if action == 'click':
            target_element.click_input()
        elif action == 'double_click':
            target_element.double_click_input()
        elif action == 'right_click':
            target_element.right_click_input()
        
        elif action == 'set_text':
            if text_to_set is None:
                return "Ошибка: для действия 'set_text' необходимо передать аргумент 'text_to_set'."
            
            target_element.click_input()
            target_element.type_keys(text_to_set, with_spaces=True)
            
        elif action == 'press_enter':
            target_element.type_keys('{ENTER}')
            
        elif action == 'get_text':
            return target_element.window_text()

        elif action == 'scroll_up':
            target_element.scroll("up", "page")
        elif action == 'scroll_down':
            target_element.scroll("down", "page")
        elif action == 'scroll_left':
            target_element.scroll("left", "page")
        elif action == 'scroll_right':
            target_element.scroll("right", "page")

        elif action == 'zoom_in':
            # Для зума используется комбинация клавиш на всем окне
            main_win.type_keys('^{PLUS}') # Ctrl + "+"
        elif action == 'zoom_out':
            # Для анзума (уменьшения)
            main_win.type_keys('^{MINUS}') # Ctrl + "-"
            
        else:
            return f"Ошибка: Неизвестное действие '{action}'."

        return f"Действие '{action}' успешно выполнено."

    except ElementNotFoundError:
        return f"Ошибка: Окно с именем '{name}' не найдено."
    except Exception as e:
        return f"Произошла непредвиденная ошибка: {type(e).__name__}: {e}"
    

@tool
def execute_bash_command(command: str) -> str:
    """Выполняет команду в терминале операционной системы.

    Используй для взаимодействия с файловой системой, выполнения скриптов и получения системной информации.
    Всегда генерируй команды, соответствующие операционной системе, которая указана в системном промпте.
    Примеры: 'dir' для Windows, 'ls -la' для Linux.
    ЗАПРЕЩЕНО: Использование разрушительных или необратимых команд (например, 'del', 'rm', 'format').

    Args:
        command (str): Текстовая строка с командой для выполнения.
    """
    # Устанавливаем тайм-аут для предотвращения "зависших" процессов
    timeout_seconds = 15
    
    try:
        # Выполняем команду
        result = subprocess.run(
            command, 
            shell=True,          # Позволяет выполнять сложные команды, но требует осторожности
            capture_output=True, # Захватывает stdout и stderr
            text=True,           # Возвращает вывод в виде текста (str)
            timeout=timeout_seconds,
            encoding="utf-8",
            errors="replace"
        )

        # Проверяем, была ли ошибка при выполнении
        if result.returncode != 0:
            return f"Ошибка выполнения команды:\nСтатус код: {result.returncode}\nStderr: {result.stderr}"
        
        # Если вывод пустой, сообщаем об этом
        if not result.stdout.strip():
            return "Команда выполнена успешно, но не произвела вывода (stdout)."

        return f"Результат выполнения:\n{result.stdout}"

    except FileNotFoundError:
        return f"Ошибка: команда '{command.split()[0]}' не найдена. Убедись, что она установлена и доступна в PATH."
    except subprocess.TimeoutExpired:
        return f"Ошибка: выполнение команды превысило тайм-аут в {timeout_seconds} секунд."
    except Exception as e:
        return f"Произошла непредвиденная ошибка: {str(e)}"