import tkinter as tk
from tkinter import font as tkFont
import queue

class SubtitleOverlay(tk.Tk):
    def __init__(self, gui_queue, stop_event_callback):
        super().__init__()
        self.gui_queue = gui_queue
        self.stop_event_callback = stop_event_callback
        self.is_agent_writing = False
        # Максимальное количество пар "вопрос-ответ" для отображения
        self.max_history_pairs = 6

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.wm_attributes("-transparentcolor", "black")
        self.config(bg='black')

        window_width = 700
        window_height = 450
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_pos = screen_width - window_width - 50
        y_pos = screen_height - window_height - 50
        self.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")

        self.status_font = tkFont.Font(family="Arial", size=14)
        self.prefix_font = tkFont.Font(family="Arial", size=16, weight="bold")
        self.main_font = tkFont.Font(family="Arial", size=16)

        self.status_label = tk.Label(self, text="", font=self.status_font, fg="#cccccc", bg="black")
        self.status_label.pack(pady=(10, 5), anchor='w', padx=10)

        self.history_text = tk.Text(self, bg="black", fg="white", font=self.main_font,
                                    padx=10, pady=10, bd=0, highlightthickness=0,
                                    wrap=tk.WORD, state='disabled')
        self.history_text.pack(expand=True, fill="both")
        
        # Спокойная и современная схема
        self.history_text.tag_configure("prefix_user", foreground="#FF7F50", font=self.prefix_font)  # Coral
        self.history_text.tag_configure("user_text", foreground="#FFDAB9", font=self.main_font)     # PeachPuff
        self.history_text.tag_configure("prefix_agent", foreground="#20B2AA", font=self.prefix_font) # LightSeaGreen
        self.history_text.tag_configure("agent_text", foreground="#AFEEEE", font=self.main_font)    # PaleTurquoise

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queue()

    def _trim_history(self):
        """Проверяет и удаляет старые сообщения, если история слишком длинная."""
        # Считаем количество реплик пользователя по префиксу "Вы: "
        user_reply_count = self.history_text.get("1.0", tk.END).count("Вы: ")
        
        if user_reply_count >= self.max_history_pairs:
            # Находим индекс второго вхождения "Вы: " (это начало второй пары)
            # Мы удаляем все до этого момента
            start_of_second_pair = self.history_text.search("Вы: ", "2.0")
            
            if start_of_second_pair:
                # Удаляем все от начала до строки, где найдена вторая пара
                self.history_text.delete("1.0", f"{start_of_second_pair} linestart")

    def _add_new_line_if_needed(self):
        if self.history_text.get('1.0', tk.END).strip():
            if self.history_text.get("end-2c", "end-1c") != "\n":
                 self.history_text.insert(tk.END, '\n')

    def on_closing(self):
        print("Окно GUI закрывается, завершаем программу...")
        self.stop_event_callback()
        self.destroy()

    def process_queue(self):
        try:
            message = self.gui_queue.get_nowait()
            msg_type = message['type']
            msg_text = message.get('text', '')

            self.history_text.config(state='normal')

            if msg_type == 'status':
                self.status_label.config(text=msg_text)
                active_statuses = ['Говорю...', 'Думаю...', 'Анализ речи...']
                if msg_text not in active_statuses and self.is_agent_writing:
                    self.is_agent_writing = False
                    self._add_new_line_if_needed()
                
                # ИГНОРИРУЕМ команду очистки, просто ничего не делаем
                # if message.get('clear_main', False):
                #     self.history_text.delete('1.0', tk.END)

            elif msg_type == 'user_input':
                if self.is_agent_writing:
                    self.is_agent_writing = False
                
                # Вызываем обрезку истории ПЕРЕД добавлением нового сообщения
                self._trim_history()
                
                self._add_new_line_if_needed()
                self.history_text.insert(tk.END, "Вы: ", "prefix_user")
                self.history_text.insert(tk.END, msg_text, "user_text")

            elif msg_type == 'agent_response_chunk':
                if not self.is_agent_writing:
                    self.is_agent_writing = True
                    self._add_new_line_if_needed()
                    self.history_text.insert(tk.END, "Агент: ", "prefix_agent")
                
                start_index = self.history_text.search("Агент:", "end-1c", backwards=True)
                if start_index:
                    self.history_text.delete(f"{start_index} + 7 chars", tk.END)
                    self.history_text.insert(tk.END, msg_text, "agent_text")

            self.history_text.see(tk.END)
            self.history_text.config(state='disabled')

        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)