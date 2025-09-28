import vosk
import pyaudio
import json
import os
import speech_recognition as sr
import whisper
import wave
import torch
import pygame
import threading
import queue
import re
import numpy as np
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig
from langchain_core.messages import HumanMessage, AIMessage
from agent.main import request_to_agent


WAKE_WORD = "джарвис"
MODEL_FOLDER_NAME = "vosk-model-small-ru-0.22"
WHISPER_MODEL_SIZE = "small"
TEMP_WAV_FILE = "temp_command.wav"
WAITING_SOUND = "S:/GitHubProjects/AI-PC-Contol/4115442.mp3"
XTTS_SR = 24000

chat_history = []

pygame.mixer.init()
activate_sound = pygame.mixer.Sound(WAITING_SOUND)

if not os.path.exists(MODEL_FOLDER_NAME):
    print(f"Ошибка: Папка с моделью '{MODEL_FOLDER_NAME}' не найдена.")
    exit()

vosk_model = vosk.Model(MODEL_FOLDER_NAME)
vosk_recognizer = vosk.KaldiRecognizer(vosk_model, 16000)

print(f"Загрузка модели Whisper '{WHISPER_MODEL_SIZE}'...")

device = "cuda" if torch.cuda.is_available() else "cpu"
torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs])

try:
    whisper_model = whisper.load_model(WHISPER_MODEL_SIZE, device=device)
    print(f"Модель Whisper успешно загружена на {device.upper()}.")
except Exception as e:
    print(f"Ошибка при загрузке модели Whisper: {e}")
    exit()

coqui_tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

pa = pyaudio.PyAudio()
stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)


def listen_command_with_whisper(recognizer, microphone):
    recognizer.pause_threshold = 2

    with microphone as source:
        activate_sound.play()
        print("Говорите вашу команду...")
        try:

            audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)

            with open(TEMP_WAV_FILE, "wb") as f:
                f.write(audio.get_wav_data())

            print("Распознавание с помощью Whisper...")

            result = whisper_model.transcribe(TEMP_WAV_FILE, language="ru", fp16=torch.cuda.is_available())
            command = result.get("text", "")

            os.remove(TEMP_WAV_FILE)

            return command.strip()
        
        except sr.WaitTimeoutError:
            return "не распознано (время вышло)"
        except sr.UnknownValueError:
            return "не распознано"
        except Exception as e:
            return f"произошла ошибка: {e}"


def sentence_chunks(text):
    pat = re.compile(r'[^\.!\?…]+[\.!\?…]+(?:["»)]?)(?:\s*)', re.DOTALL)
    pos = 0
    for m in pat.finditer(text):
        yield m.group(0)
        pos = m.end()
    if pos < len(text):
        yield text[pos:]


def speak_streaming(text, speaker_wav="test2.mp3", language="ru", speed=5.0, volume=0.5):
    q = queue.Queue(maxsize=64)

    def producer():
        with torch.no_grad():
            for sent in sentence_chunks(text):
                try:
                    for wav in coqui_tts.tts_stream(text=sent, speaker_wav=speaker_wav, language=language, speed=speed):
                        wav = np.asarray(wav, dtype=np.float32).flatten()
                        wav = (wav * volume).clip(-1.0, 1.0)
                        pcm16 = (wav * 32767.0).astype(np.int16).tobytes()
                        q.put(pcm16)
                except Exception:
                    wav = coqui_tts.tts(text=sent, speaker_wav=speaker_wav, language=language, speed=speed)
                    wav = np.asarray(wav, dtype=np.float32).flatten()
                    wav = (wav * volume).clip(-1.0, 1.0)
                    pcm16 = (wav * 32767.0).astype(np.int16).tobytes()
                    q.put(pcm16)
        q.put(None)

    def consumer():
        out = pa.open(format=pyaudio.paInt16, channels=1, rate=XTTS_SR, output=True, frames_per_buffer=1024)
        try:
            while True:
                data = q.get()
                if data is None:
                    break
                out.write(data)
        finally:
            out.stop_stream()
            out.close()

    t_prod = threading.Thread(target=producer, daemon=True)
    t_cons = threading.Thread(target=consumer, daemon=True)
    t_cons.start()
    t_prod.start()
    t_prod.join()
    t_cons.join()


stream.start_stream()
print(f"\nСистема активирована. Ожидание кодового слова '{WAKE_WORD}'...")


try:
    while True:
        data = stream.read(4096, exception_on_overflow=False)

        if vosk_recognizer.AcceptWaveform(data):
            result_json = vosk_recognizer.Result()
            result_dict = json.loads(result_json)
            text = result_dict.get("text", "")

            if WAKE_WORD in text:
                print(f"Кодовое слово '{WAKE_WORD}' обнаружено!")
            
                r = sr.Recognizer()
                mic = sr.Microphone(sample_rate=16000)
                
                with mic as source:

                    print("Калибровка уровня шума...")
                    r.adjust_for_ambient_noise(source, duration=0.5)

                while True:

                    command = listen_command_with_whisper(r, mic)

                    if command and "не распознано" not in command and "ошибка" not in command:


                        print(f"Выполнение запроса: '{command}'")

                        chat_history.append(HumanMessage(command))

                        result = request_to_agent(chat_history)

                        chat_history = result

                        result = result[-1].content

                        if result != "":
                            speak_streaming(result, speaker_wav="test.wav", language="ru", speed=5.0, volume=0.5)
                            
                        print(f"Результат выполнения команды: {result}")
                        print("Слушаю следующую команду...")

                    elif "время вышло" in command:
                        print("Время ожидания истекло.")
                        break
                    else:
                        print(f"Команду не удалось распознать. ({command})")
                        break

                print(f"\nСнова жду кодовое слово '{WAKE_WORD}'...")
                vosk_recognizer.Reset()

except KeyboardInterrupt:
    print("\nПрограмма остановлена.")

finally:
    if stream.is_active():
        stream.stop_stream()
        stream.close()
    pa.terminate()
    if os.path.exists(TEMP_WAV_FILE):
        os.remove(TEMP_WAV_FILE)