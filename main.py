import vosk
import pyaudio
import json
import os
import torch
import pygame
import threading
import queue
import re
import numpy as np
import whisper
import webrtcvad
import time
from collections import deque
from openai import BadRequestError
import pyttsx3

from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig
from langchain_core.messages import HumanMessage
from agent.main import request_to_agent

from gui.overlay import SubtitleOverlay
from utils.media_utils import *


ASR_ENGINE = 'whisper'
TTS_ENGINE = 'pyttsx3'

WAKE_WORD = "джарвис"
SOUND_MINUS_WORD = "тише"
SOUND_PLUS_WORD = "громче"
PAUSE_WORD = "пауза"
PLAY_WORD = "продолжи"
NEXT_WORD = "дальше"
BACK_WORD = "назад"
UP_WORD = "вверх"
DOWN_WORD = "вниз"

MODEL_FOLDER_NAME = "vosk-model-small-ru-0.22"
WHISPER_MODEL_NAME = "small"
WAITING_SOUND = "4115442.mp3"
XTTS_SR = 24000
INPUT_SAMPLE_RATE = 16000
INPUT_CHANNELS = 1
INPUT_FORMAT = pyaudio.paInt16
VAD_AGGRESSIVENESS = 3
VAD_FRAME_MS = 30
VAD_CHUNK_SIZE = int(INPUT_SAMPLE_RATE * (VAD_FRAME_MS / 1000.0))
VAD_SILENCE_TIMEOUT_MS = 1500
VAD_PRE_BUFFER_MS = 300
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
FOLLOW_UP_TIMEOUT_SECONDS = 5

chat_history = []
gui_queue = queue.Queue()
stop_event = threading.Event()

pygame.mixer.init()
activate_sound = pygame.mixer.Sound(WAITING_SOUND)

if not os.path.exists(MODEL_FOLDER_NAME):
    print(f"Ошибка: Папка с моделью Vosk '{MODEL_FOLDER_NAME}' не найдена.")
    exit()
vosk_model = vosk.Model(MODEL_FOLDER_NAME)

coqui_tts = None
pyttsx3_engine = None

if TTS_ENGINE == 'xtts':
    print("Загрузка модели TTS (Coqui XTTS)...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs])
    try:
        coqui_tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        print(f"Модель TTS (XTTS) успешно загружена на {device.upper()}.")
    except Exception as e:
        print(f"Ошибка при загрузке модели XTTS: {e}")
        exit()
elif TTS_ENGINE == 'pyttsx3':
    print("Инициализация системного движка TTS (pyttsx3)...")
    try:
        pyttsx3_engine = pyttsx3.init()
        voices = pyttsx3_engine.getProperty('voices')
        russian_voice_found = False
        for voice in voices:
            if 'russian' in voice.name.lower() or 'ru' in voice.id.lower():
                pyttsx3_engine.setProperty('voice', voice.id)
                russian_voice_found = True
                print(f"Найден и установлен русский голос: {voice.name}")
                break
        if not russian_voice_found:
            print("Предупреждение: Русский голос для pyttsx3 не найден. Будет использован голос по умолчанию.")
        print("Движок pyttsx3 успешно инициализирован.")
    except Exception as e:
        print(f"Ошибка при инициализации pyttsx3: {e}")
        exit()
else:
    print(f"Ошибка: Неизвестный движок TTS '{TTS_ENGINE}'. Доступные варианты: 'xtts', 'pyttsx3'.")
    exit()

whisper_model = None
if ASR_ENGINE == 'whisper':
    print(f"Загрузка модели Whisper ({WHISPER_MODEL_NAME})...")
    try:
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
        print("Модель Whisper успешно загружена.")
    except Exception as e:
        print(f"Ошибка при загрузке модели Whisper: {e}")
        exit()

pa = pyaudio.PyAudio()
stream = pa.open(
    format=INPUT_FORMAT,
    channels=INPUT_CHANNELS,
    rate=INPUT_SAMPLE_RATE,
    input=True,
    frames_per_buffer=VAD_CHUNK_SIZE
)

def sentence_chunks(text):
    pat = re.compile(r'[^\.!\?…]+[\.!\?…]+(?:["»)]?)(?:\s*)', re.DOTALL)
    pos = 0
    full_response = ""
    for m in pat.finditer(text):
        chunk = m.group(0)
        full_response += chunk
        gui_queue.put({'type': 'agent_response_chunk', 'text': full_response})
        yield chunk
        pos = m.end()
    if pos < len(text):
        remaining_text = text[pos:]
        full_response += remaining_text
        gui_queue.put({'type': 'agent_response_chunk', 'text': full_response})
        yield remaining_text

def speak_streaming(text, speaker_wav="test5.mp3", language="ru", speed=5.0, volume=0.5):
    q = queue.Queue(maxsize=64)
    def producer():
        with torch.no_grad():
            for sent in sentence_chunks(text):
                try:
                    for wav_chunk in coqui_tts.tts_stream(text=sent, speaker_wav=speaker_wav, language=language, speed=speed):
                        wav_chunk = (np.asarray(wav_chunk, dtype=np.float32).flatten() * volume).clip(-1.0, 1.0)
                        pcm16 = (wav_chunk * 32767.0).astype(np.int16).tobytes()
                        q.put(pcm16)
                except Exception:
                    wav = coqui_tts.tts(text=sent, speaker_wav=speaker_wav, language=language, speed=speed)
                    wav = (np.asarray(wav, dtype=np.float32).flatten() * volume).clip(-1.0, 1.0)
                    pcm16 = (wav * 32767.0).astype(np.int16).tobytes()
                    q.put(pcm16)
        q.put(None)

    def consumer():
        out = pa.open(format=pyaudio.paInt16, channels=1, rate=XTTS_SR, output=True)
        try:
            while not stop_event.is_set():
                try:
                    data = q.get(timeout=0.1)
                    if data is None: break
                    out.write(data)
                except queue.Empty:
                    continue
        finally:
            out.stop_stream()
            out.close()

    t_prod = threading.Thread(target=producer, daemon=True)
    t_cons = threading.Thread(target=consumer, daemon=True)
    t_prod.start()
    t_cons.start()
    t_prod.join()
    t_cons.join()

def speak_pyttsx3(text, volume=0.8):
    pyttsx3_engine.setProperty('volume', float(volume))
    pat = re.compile(r'[^\.!\?…]+[\.!\?…]+(?:["»)]?)(?:\s*)', re.DOTALL)
    sentences = []
    pos = 0
    for m in pat.finditer(text):
        sentences.append(m.group(0).strip())
        pos = m.end()
    if pos < len(text):
        remaining = text[pos:].strip()
        if remaining:
            sentences.append(remaining)
    
    if not sentences:
        sentences = [text]
    
    full_response = ""
    for sentence in sentences:
        if stop_event.is_set():
            pyttsx3_engine.stop()
            return
        
        full_response += sentence + " "
        gui_queue.put({'type': 'agent_response_chunk', 'text': full_response.strip()})
        
        pyttsx3_engine.say(sentence)
        pyttsx3_engine.runAndWait()


def listen_with_vad_whisper(audio_stream, model, activation_timeout=None):
    if activation_timeout:
        print(f"Ожидание команды ({activation_timeout} сек)...")
    else:
        print("Слушаю команду (Whisper)...")

    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    frames_per_second = int(INPUT_SAMPLE_RATE / VAD_CHUNK_SIZE)
    silence_frames_needed = int(frames_per_second * (VAD_SILENCE_TIMEOUT_MS / 1000.0))
    pre_buffer_size = int(frames_per_second * (VAD_PRE_BUFFER_MS / 1000.0))
    pre_buffer = deque(maxlen=pre_buffer_size)
    speech_frames = []
    is_speaking = False
    silent_frames_count = 0
    start_time = time.time()

    audio_stream.stop_stream()
    audio_stream.start_stream()

    while not stop_event.is_set():
        try:
            if not is_speaking and activation_timeout and (time.time() - start_time > activation_timeout):
                print("Таймаут ожидания речи.")
                return "время вышло"

            chunk = audio_stream.read(VAD_CHUNK_SIZE, exception_on_overflow=False)
            if len(chunk) < VAD_CHUNK_SIZE * 2: continue

            is_speech = vad.is_speech(chunk, INPUT_SAMPLE_RATE)

            if is_speech:
                if not is_speaking:
                    print("Обнаружена речь...")
                    gui_queue.put({'type': 'status', 'text': 'Говорите...'})
                    is_speaking = True
                    speech_frames.extend(list(pre_buffer))
                speech_frames.append(chunk)
                silent_frames_count = 0
            else:
                if not is_speaking:
                    pre_buffer.append(chunk)
                else:
                    speech_frames.append(chunk)
                    silent_frames_count += 1
                    if silent_frames_count > silence_frames_needed:
                        print("Конец фразы (таймаут по тишине).")
                        break
        except IOError as e:
            print(f"Ошибка чтения потока: {e}")
            break
    
    if stop_event.is_set(): return "ошибка"

    if not speech_frames or not is_speaking:
        return "время вышло"

    print("Обработка запроса моделью Whisper...")
    gui_queue.put({'type': 'status', 'text': 'Анализ речи...'})
    audio_data = b''.join(speech_frames)
    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
    result = model.transcribe(audio_np, language="ru", fp16=torch.cuda.is_available())
    command = result.get("text", "").strip()
    return command if command else "время вышло"

def listen_with_vosk(audio_stream, recognizer):
    print("Слушаю команду (Vosk)...")
    recognizer.Reset()
    while not stop_event.is_set():
        try:
            data = audio_stream.read(4096, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result_json = recognizer.FinalResult()
                result_dict = json.loads(result_json)
                command = result_dict.get("text", "")
                if command:
                    print("Команда распознана.")
                    return command.strip()
        except IOError as e:
            print(f"Ошибка чтения потока: {e}")
            break
    return "время вышло"

def listen_for_command(audio_stream, play_sound=True, activation_timeout=None):
    if play_sound:
        activate_sound.play()
    if ASR_ENGINE == 'whisper':
        return listen_with_vad_whisper(audio_stream, whisper_model, activation_timeout=activation_timeout)
    elif ASR_ENGINE == 'vosk':
        vosk_command_recognizer = vosk.KaldiRecognizer(vosk_model, INPUT_SAMPLE_RATE)
        return listen_with_vosk(audio_stream, vosk_command_recognizer)
    else:
        print(f"Ошибка: Неизвестный движок распознавания '{ASR_ENGINE}'")
        return "ошибка"

def wait_for_wake_word(audio_stream):
    recognizer = vosk.KaldiRecognizer(vosk_model, INPUT_SAMPLE_RATE)
    recognizer.SetWords(True)
    
    print(f"\nОжидание команд ({WAKE_WORD}, {SOUND_PLUS_WORD}, {SOUND_MINUS_WORD}, {PAUSE_WORD}, {PLAY_WORD})...")

    while not stop_event.is_set():
        try:
            data = audio_stream.read(4096, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result_json = recognizer.Result()
                result_dict = json.loads(result_json)
                text = result_dict.get("text", "")

                if SOUND_MINUS_WORD in text:
                    print(f"Быстрая команда: '{SOUND_MINUS_WORD}'. Уменьшаю громкость.")
                    sound_minus()
                    continue

                if SOUND_PLUS_WORD in text:
                    print(f"Быстрая команда: '{SOUND_PLUS_WORD}'. Увеличиваю громкость.")
                    sound_plus()
                    continue

                if PAUSE_WORD in text:
                    print(f"Быстрая команда: '{PAUSE_WORD}'. Ставлю на паузу.")
                    play_pause()
                    continue

                if PLAY_WORD in text:
                    print(f"Быстрая команда: '{PLAY_WORD}'. Продолжаю воспроизведение.")
                    play_pause()
                    continue

                if NEXT_WORD in text:
                    print(f"Быстрая команда: '{NEXT_WORD}'. Следующий медия.")
                    next_media()
                    continue
                        
                if BACK_WORD in text:
                    print(f"Быстрая команда: '{BACK_WORD}'. Предыдущая медия.")
                    back_media()
                    continue

                if UP_WORD in text:
                    print(f"Быстрая команда: '{UP_WORD}'. Вверх.")
                    up()

                if DOWN_WORD in text:
                    print(f"Быстрая команда: '{UP_WORD}'. Вниз")
                    down()

                if WAKE_WORD in text:
                    print(f"▶️ Кодовое слово '{WAKE_WORD}' обнаружено!")
                    command_part = text.split(WAKE_WORD, 1)[-1].strip()
                    return command_part

        except IOError as e:
            print(f"Ошибка чтения потока в wait_for_wake_word: {e}")
            break
            
    return None

def voice_assistant_logic():
    global chat_history
    stream.start_stream()
    print(f"\n✅ Система активирована. Движок ASR: {ASR_ENGINE.upper()}. Движок TTS: {TTS_ENGINE.upper()}.")
    try:
        while not stop_event.is_set():
            gui_queue.put({'type': 'status', 'text': f'Ожидание "{WAKE_WORD}"...', 'clear_main': True})
            command = wait_for_wake_word(stream)
            if stop_event.is_set(): break

            if not command:
                gui_queue.put({'type': 'status', 'text': 'Слушаю команду...'})
                command = listen_for_command(stream)
            else:
                activate_sound.play()

            while command and "время вышло" not in command and "ошибка" not in command:
                if stop_event.is_set(): break
                
                gui_queue.put({'type': 'status', 'text': '', 'clear_main': True})
                
                print(f"Выполнение запроса: '{command}'")
                chat_history.append(HumanMessage(content=command))
                gui_queue.put({'type': 'status', 'text': 'Думаю...'})
                response_history = None
                for attempt in range(MAX_RETRIES):
                    if stop_event.is_set(): break
                    try:
                        response_history = request_to_agent(chat_history)
                        break
                    except BadRequestError as e:
                        print(f"Ошибка (попытка {attempt + 1}/{MAX_RETRIES}): {e}")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY_SECONDS)
                        else:
                            print("Не удалось получить ответ от LLM.")
                            response_history = None
                    except Exception as e:
                        print(f"Непредвиденная ошибка: {e}")
                        response_history = None
                        break
                
                if stop_event.is_set(): break

                if response_history:
                    chat_history = response_history
                    response_text = response_history[-1].content
                else:
                    response_text = "Произошла ошибка при обработке запроса."

                if response_text:
                    gui_queue.put({'type': 'status', 'text': 'Говорю...'})
                    print(f"Ответ агента: {response_text}")
                    
                    if TTS_ENGINE == 'xtts':
                        speak_streaming(response_text)
                    elif TTS_ENGINE == 'pyttsx3':
                        speak_pyttsx3(response_text)
                else:
                    print("Агент вернул пустой ответ.")
                
                gui_queue.put({'type': 'status', 'text': 'Слушаю продолжение...'})
                command = listen_for_command(stream, play_sound=False, activation_timeout=FOLLOW_UP_TIMEOUT_SECONDS)

            print(f"\n🔁 Снова жду кодовое слово '{WAKE_WORD}'...")
    except Exception as e:
        print(f"Критическая ошибка в потоке ассистента: {e}")
    finally:
        print("Поток ассистента завершает работу.")
        if stream.is_active():
            stream.stop_stream()
            stream.close()
        pa.terminate()

def shutdown_app():
    stop_event.set()

assistant_thread = threading.Thread(target=voice_assistant_logic, daemon=True)
assistant_thread.start()

app = SubtitleOverlay(gui_queue=gui_queue, stop_event_callback=shutdown_app)
app.mainloop()

print("Основной поток: ожидание завершения рабочего потока...")
assistant_thread.join(timeout=2)
print("Программа полностью завершена.")