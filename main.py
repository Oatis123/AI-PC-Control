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
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig
from langchain_core.messages import HumanMessage
from agent.main import request_to_agent

WAKE_WORD = "джарвис"
MODEL_FOLDER_NAME = "vosk-model-small-ru-0.22"
WAITING_SOUND = "4115442.mp3"
XTTS_SR = 24000
INPUT_SAMPLE_RATE = 16000
INPUT_FRAMES_PER_BUFFER = 4096
COMMAND_TIMEOUT_SECONDS = 10
FOLLOW_UP_TIMEOUT_SECONDS = 8 # Время ожидания следующей команды

chat_history = []

pygame.mixer.init()
activate_sound = pygame.mixer.Sound(WAITING_SOUND)

if not os.path.exists(MODEL_FOLDER_NAME):
    print(f"Ошибка: Папка с моделью '{MODEL_FOLDER_NAME}' не найдена.")
    exit()

vosk_model = vosk.Model(MODEL_FOLDER_NAME)
vosk_recognizer = vosk.KaldiRecognizer(vosk_model, INPUT_SAMPLE_RATE)
vosk_recognizer.SetWords(True)

print("Загрузка модели TTS...")
device = "cuda" if torch.cuda.is_available() else "cpu"
torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs])
try:
    coqui_tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print(f"Модель TTS успешно загружена на {device.upper()}.")
except Exception as e:
    print(f"Ошибка при загрузке модели TTS: {e}")
    exit()

pa = pyaudio.PyAudio()
stream = pa.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=INPUT_SAMPLE_RATE,
    input=True,
    frames_per_buffer=INPUT_FRAMES_PER_BUFFER
)


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
                    for wav_chunk in coqui_tts.tts_stream(text=sent, speaker_wav=speaker_wav, language=language, speed=speed):
                        wav_chunk = np.asarray(wav_chunk, dtype=np.float32).flatten()
                        wav_chunk = (wav_chunk * volume).clip(-1.0, 1.0)
                        pcm16 = (wav_chunk * 32767.0).astype(np.int16).tobytes()
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


def listen_for_command_vosk(audio_stream, recognizer, timeout_seconds):
    activate_sound.play()
    print(f"Слушаю команду ({timeout_seconds} сек)...")
    max_chunks = int((INPUT_SAMPLE_RATE / INPUT_FRAMES_PER_BUFFER) * timeout_seconds)
    
    for i in range(max_chunks):
        data = audio_stream.read(INPUT_FRAMES_PER_BUFFER, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result_json = recognizer.FinalResult()
            result_dict = json.loads(result_json)
            command = result_dict.get("text", "")
            if command:
                return command.strip()
    
    return "время вышло"

stream.start_stream()
print(f"\n✅ Система активирована. Ожидание кодового слова '{WAKE_WORD}'...")

try:
    while True:
        data = stream.read(INPUT_FRAMES_PER_BUFFER, exception_on_overflow=False)

        if vosk_recognizer.AcceptWaveform(data):
            result_json = vosk_recognizer.Result()
            result_dict = json.loads(result_json)
            text = result_dict.get("text", "")

            if WAKE_WORD in text:
                print(f"▶️ Кодовое слово '{WAKE_WORD}' обнаружено!")
                
                command = text.replace(WAKE_WORD, "").strip()

                if not command:
                    command = listen_for_command_vosk(stream, vosk_recognizer, COMMAND_TIMEOUT_SECONDS)
                else:
                    activate_sound.play()

                # Начало цикла диалога
                while command and "время вышло" not in command:
                    print(f"Выполнение запроса: '{command}'")

                    chat_history.append(HumanMessage(content=command))
                    response_history = request_to_agent(chat_history)
                    
                    if response_history:
                        chat_history = response_history
                        response_text = response_history[-1].content
                    else:
                        response_text = "Произошла ошибка при обработке запроса."

                    if response_text:
                        print(f"Ответ агента: {response_text}")
                        speak_streaming(response_text, speaker_wav="test.wav", language="ru", speed=5.0, volume=0.5)
                    else:
                        print("Агент вернул пустой ответ.")
                    
                    # Ожидание следующей команды
                    command = listen_for_command_vosk(stream, vosk_recognizer, FOLLOW_UP_TIMEOUT_SECONDS)

                # Если цикл завершился из-за тайм-аута или пустой команды
                if "время вышло" in command:
                    print("Время ожидания следующей команды истекло.")
                else:
                    print(f"Команду не удалось распознать. ({command})")

                print(f"\n🔁 Снова жду кодовое слово '{WAKE_WORD}'...")
                vosk_recognizer.Reset()

except KeyboardInterrupt:
    print("\nПрограмма остановлена.")

finally:
    print("Завершение работы...")
    if stream.is_active():
        stream.stop_stream()
        stream.close()
    pa.terminate()