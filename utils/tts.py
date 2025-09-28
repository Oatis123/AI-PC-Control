from TTS.api import TTS

def tts(text, device):
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print("Модель загружена. Генерируем речь с кастомным голосом...")
    tts.tts_to_file(
    text=text,
    file_path="output_custom.wav",
    speaker_wav="path/to/your/voice_sample.wav", # <--- УКАЖИТЕ ПУТЬ К ВАШЕМУ АУДИО
    language="ru"
    )
    print("Аудиофайл 'output_custom.wav' успешно создан!")