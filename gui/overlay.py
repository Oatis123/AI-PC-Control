import tkinter as tk
from tkinter import font as tkFont
import queue

class SubtitleOverlay(tk.Tk):
    def __init__(self, gui_queue, stop_event_callback):
        super().__init__()
        self.gui_queue = gui_queue
        self.stop_event_callback = stop_event_callback

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.wm_attributes("-transparentcolor", "black")
        self.config(bg='black')

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        self.border_color_idle = "#6E6E6E"
        self.border_color_listening = "#FFFFFF"
        self.border_color_thinking = "#FF8C00"
        self.border_color_speaking = "#00E767"

        self.top_border = tk.Frame(self, bg=self.border_color_idle, height=5)
        self.top_border.pack(side='top', fill='x')
        self.bottom_border = tk.Frame(self, bg=self.border_color_idle, height=5)
        self.bottom_border.pack(side='bottom', fill='x')
        self.left_border = tk.Frame(self, bg=self.border_color_idle, width=5)
        self.left_border.pack(side='left', fill='y')
        self.right_border = tk.Frame(self, bg=self.border_color_idle, width=5)
        self.right_border.pack(side='right', fill='y')

        center_frame = tk.Frame(self, bg='black')
        center_frame.pack(expand=True, fill='both')

        subtitle_width = int(screen_width * 0.8)
        subtitle_height = 200

        self.content_frame = tk.Frame(center_frame, bg='black', width=subtitle_width, height=subtitle_height)
        self.content_frame.pack(side='bottom', pady=30)
        self.content_frame.pack_propagate(False)

        self.status_font = tkFont.Font(family="Arial", size=16)
        self.main_font = tkFont.Font(family="Arial", size=22)

        self.status_label = tk.Label(self.content_frame, text="", font=self.status_font, fg="#cccccc", bg="black")
        self.status_label.pack(pady=(5, 2))

        self.agent_text_label = tk.Label(
            self.content_frame,
            text="",
            font=self.main_font,
            fg="#AFEEEE",
            bg="black",
            wraplength=subtitle_width - 20
        )
        self.agent_text_label.pack(expand=True, fill="both", padx=10, pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queue()

    def set_border_color(self, color):
        self.top_border.config(bg=color)
        self.bottom_border.config(bg=color)
        self.left_border.config(bg=color)
        self.right_border.config(bg=color)

    def on_closing(self):
        print("Окно GUI закрывается, завершаем программу...")
        self.stop_event_callback()
        self.destroy()

    def process_queue(self):
        try:
            message = self.gui_queue.get_nowait()
            msg_type = message['type']
            msg_text = message.get('text', '')

            if msg_type == 'status':
                if msg_text.strip():
                    self.status_label.config(text=msg_text)
                
                if message.get('clear_main'):
                    self.agent_text_label.config(text="")

                if 'Ожидание' in msg_text:
                    self.set_border_color(self.border_color_idle)
                elif msg_text in ['Слушаю команду...', 'Слушаю продолжение...']:
                    self.set_border_color(self.border_color_listening)
                elif msg_text == 'Думаю...':
                    self.set_border_color(self.border_color_thinking)
                elif msg_text == 'Говорю...':
                    self.set_border_color(self.border_color_speaking)

            elif msg_type == 'agent_response_chunk':
                self.agent_text_label.config(text=msg_text)

        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)