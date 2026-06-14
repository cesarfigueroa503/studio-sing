from PySide6.QtMultimedia import QAudioDecoder
from PySide6.QtCore import QUrl, QEventLoop
import sys

def test_decoder():
    decoder = QAudioDecoder()
    decoder.setSource(QUrl.fromLocalFile("dummy.mp4"))
    
    loop = QEventLoop()
    decoder.finished.connect(loop.quit)
    decoder.errorOccurred.connect(lambda e: (print(f"Error: {e}"), loop.quit()))
    
    print("Iniciando decodificación...")
    decoder.start()
    # Esto no funcionará sin un archivo real, pero vemos si existe la clase y no da error inmediato.
    print("Clase QAudioDecoder disponible.")

if __name__ == "__main__":
    test_decoder()
