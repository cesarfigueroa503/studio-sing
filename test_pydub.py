from pydub import AudioSegment
import sys

try:
    # Intenta cargar un archivo que no existe solo para ver si tira error de ffmpeg
    AudioSegment.from_file("dummy.mp4")
except FileNotFoundError:
    print("FileNotFoundError: El archivo no existe, pero pydub intentó cargarlo.")
except Exception as e:
    print(f"Error: {e}")
