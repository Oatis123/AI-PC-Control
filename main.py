import vosk
import pyaudio
import json
import os
import speech_recognition as sr
import whisper
import wave

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
    whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
    print("Модель Whisper успешно загружена.")
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
stream.start_stream()

def listen_command_with_whisper():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Калибровка уровня шума...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("Говорите вашу команду...")
        try:
            audio = r.listen(source)
            
            with wave.open(TEMP_WAV_FILE, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(audio.get_wav_data())

            print("Распознавание с помощью Whisper...")
            result = whisper_model.transcribe(TEMP_WAV_FILE, language="ru", fp16=False)
            command = result.get("text", "")
            
            os.remove(TEMP_WAV_FILE)
            
            return command
            
        except sr.UnknownValueError:
            return "не распознано"
        except Exception as e:
            return f"произошла ошибка: {e}"

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
                
                if command and command != "не распознано":
                    print(f"Вы сказали: '{command.strip()}'")
                else:
                    print("Команду не удалось распознать.")

                print(f"\nСнова жду кодовое слово '{WAKE_WORD}'...")

except KeyboardInterrupt:
    print("\nПрограмма остановлена.")
finally:
    stream.stop_stream()
    stream.close()
    pa.terminate()