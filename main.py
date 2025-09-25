import vosk
import pyaudio
import json
import os
import speech_recognition as sr
import whisper
import wave
import torch
from agent.main import request_to_agent

WAKE_WORD = "компьютер"
MODEL_FOLDER_NAME = "vosk-model-small-ru-0.22"
WHISPER_MODEL_SIZE = "small"
TEMP_WAV_FILE = "temp_command.wav"

if not os.path.exists(MODEL_FOLDER_NAME):
    print(f"Ошибка: Папка с моделью '{MODEL_FOLDER_NAME}' не найдена.")
    exit()

vosk_model = vosk.Model(MODEL_FOLDER_NAME)
vosk_recognizer = vosk.KaldiRecognizer(vosk_model, 16000)

print(f"Загрузка модели Whisper '{WHISPER_MODEL_SIZE}'...")

try:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    whisper_model = whisper.load_model(WHISPER_MODEL_SIZE, device=device)
    print(f"Модель Whisper успешно загружена на {device.upper()}.")
except Exception as e:
    print(f"Ошибка при загрузке модели Whisper: {e}")
    exit()

pa = pyaudio.PyAudio()
stream = pa.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=8192
)

def listen_command_with_whisper():
    r = sr.Recognizer()
    r.pause_threshold = 3.0
    with sr.Microphone(sample_rate=16000) as source:
        print("Калибровка уровня шума...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("Говорите вашу команду...")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=20)
            
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
                
                command = listen_command_with_whisper()
                
                if command and "не распознано" not in command and "ошибка" not in command:
                    print(f"Выполнение запроса: '{command}'")
                    result = request_to_agent(command)
                    print(f"Результат выполнения команды: {result}")
                else:
                    print(f"Команду не удалось распознать. ({command})")

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