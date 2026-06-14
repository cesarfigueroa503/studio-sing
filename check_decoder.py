from PySide6.QtMultimedia import QAudioDecoder
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
decoder = QAudioDecoder()
print("Attributes of QAudioDecoder:")
for attr in dir(decoder):
    if "error" in attr.lower() or "signal" in attr.lower() or "finished" in attr.lower() or "ready" in attr.lower():
        print(attr)
