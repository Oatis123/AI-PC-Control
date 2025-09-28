import vosk
import pyaudio
import json
import os
import speech_recognition as sr
import whisper
import wave
import torch
import pygame
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig
from agent.main import request_to_agent
from utils.tts import tts
import numpy as np

WAKE_WORD = "джарвис"
MODEL_FOLDER_NAME = "vosk-model-small-ru-0.22"
WHISPER_MODEL_SIZE = "small"
TEMP_WAV_FILE = "temp_command.wav"
WAITING_SOUND = "S:/GitHubProjects/AI-PC-Contol/4115442.mp3"

pygame.mixer.init()
activate_sound = pygame.mixer.Sound(WAITING_SOUND)

if not os.path.exists(MODEL_FOLDER_NAME):
    print(f"Ошибка: Папка с моделью '{MODEL_FOLDER_NAME}' не найдена.")
    exit()

vosk_model = vosk.Model(MODEL_FOLDER_NAME)
vosk_recognizer = vosk.KaldiRecognizer(vosk_model, 16000)

print(f"Загрузка модели Whisper '{WHISPER_MODEL_SIZE}'...")

device = "cuda" if torch.cuda.is_available() else "cpu"
torch.serialization.add_safe_globals([
    XttsConfig,
    XttsAudioConfig,
    BaseDatasetConfig,
    XttsArgs
])

try:
    whisper_model = whisper.load_model(WHISPER_MODEL_SIZE, device=device)
    print(f"Модель Whisper успешно загружена на {device.upper()}.")
except Exception as e:
    print(f"Ошибка при загрузке модели Whisper: {e}")
    exit()

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

pa = pyaudio.PyAudio()
stream = pa.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=8192
)


def play_audio_stream(tts_instance, text_to_speak, speaker_wav_path, language_code):
    sample_rate = tts_instance.synthesizer.output_sample_rate
    p = pyaudio.PyAudio()
    
    stream_out = p.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=sample_rate,
                        output=True)

    print("Начинаю потоковую генерацию и воспроизведение...")
    try:
        audio_stream = tts_instance.tts_stream(
            text=text_to_speak,
            speaker_wav=speaker_wav_path,
            language=language_code,
            speed=2.0
        )
        
        for chunk in audio_stream:
            audio_data = chunk.cpu().numpy().astype(np.float32).tobytes()
            stream_out.write(audio_data)

    finally:
        stream_out.stop_stream()
        stream_out.close()
        p.terminate()
        print("Воспроизведение завершено.")


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
                        result = request_to_agent(command)
                        
                        if result and result.strip() != "":
                            play_audio_stream(
                                tts_instance=tts,
                                text_to_speak=result,
                                speaker_wav_path="test2.mp3",
                                language_code="ru"
                            )

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