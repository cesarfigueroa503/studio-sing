from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QFileDialog, QSlider)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
import sys
import threading
from engine.audio_engine import AudioEngine
from ui.playback_window import PlaybackWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Grabadora de Voz Karaoke")
        self.setMinimumSize(800, 600)
        
        self.engine = AudioEngine()
        self.engine.start()
        
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        
        # Audio del video será usado directamente al grabar para sincronización perfecta
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5) 
        
        self.playback_window = None
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # --- Cabecera y Controles de Grabación ---
        controls_panel = QFrame()
        controls_layout = QVBoxLayout(controls_panel)
        
        # Fila superior de botones
        buttons_layout = QHBoxLayout()
        self.btn_load_karaoke = QPushButton("Cargar Video Karaoke")
        self.btn_load_karaoke.clicked.connect(self.load_karaoke)
        
        self.btn_record = QPushButton("Grabar")
        self.btn_record.setObjectName("btn_record")
        self.btn_record.setEnabled(False)
        self.btn_record.clicked.connect(self.toggle_recording)
        self.btn_monitor = QPushButton("Monitoreo: OFF")
        self.btn_monitor.setObjectName("btn_monitor")
        self.btn_monitor.setCheckable(True)
        self.btn_monitor.setChecked(False) # Monitoreo inicializado en OFF
        self.btn_monitor.clicked.connect(self.toggle_monitor)

        buttons_layout.addWidget(self.btn_load_karaoke)
        buttons_layout.addWidget(self.btn_record)
        buttons_layout.addWidget(self.btn_monitor)
        controls_layout.addLayout(buttons_layout)


        # Fila de volúmenes (Video y Monitoreo)
        volumes_layout = QHBoxLayout()
        
        # Control Volumen Video/Pista (Nativo durante grabación)
        video_vol_layout = QVBoxLayout()
        video_vol_layout.addWidget(QLabel("Volumen Música/Video"))
        self.video_vol_slider = QSlider(Qt.Horizontal)
        self.video_vol_slider.setRange(0, 100)
        self.video_vol_slider.setValue(50)
        self.video_vol_slider.valueChanged.connect(self.update_volumes)
        video_vol_layout.addWidget(self.video_vol_slider)
        volumes_layout.addLayout(video_vol_layout)

        # Control Volumen Monitoreo Voz
        monitor_vol_layout = QVBoxLayout()
        monitor_vol_layout.addWidget(QLabel("Volumen Monitoreo Voz"))
        self.monitor_vol_slider = QSlider(Qt.Horizontal)
        self.monitor_vol_slider.setRange(0, 100)
        self.monitor_vol_slider.setValue(80)
        self.monitor_vol_slider.valueChanged.connect(self.update_volumes)
        monitor_vol_layout.addWidget(self.monitor_vol_slider)
        volumes_layout.addLayout(monitor_vol_layout)

        controls_layout.addLayout(volumes_layout)
        main_layout.addWidget(controls_panel)
        
        # --- Area de Video ---
        video_frame = QFrame()
        video_frame.setMinimumHeight(400)
        video_layout = QVBoxLayout(video_frame)
        video_layout.addWidget(self.video_widget)
        main_layout.addWidget(video_frame)

        self.status_label = QLabel("Carga un video para empezar el Karaoke")
        main_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)

    def update_volumes(self):
        # Actualizar volúmenes
        vol = self.video_vol_slider.value() / 100.0
        self.audio_output.setVolume(vol) # Volumen nativo del player
        self.engine.accompaniment_volume = vol # Volumen para la edición posterior
        self.engine.monitoring_volume = self.monitor_vol_slider.value() / 100.0

    def load_karaoke(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Video Karaoke", "", "Videos (*.mp4 *.mkv *.avi *.wmv)")
        if path:
            self.status_label.setText("Extrayendo audio de la pista...")
            self.btn_load_karaoke.setEnabled(False)
            
            def on_extracted(success):
                if success:
                    self.media_player.setSource(QUrl.fromLocalFile(path))
                    self.btn_record.setEnabled(True)
                    self.status_label.setText("Listo para grabar!")
                else:
                    self.status_label.setText("Error al extraer audio del video.")
                self.btn_load_karaoke.setEnabled(True)

            self.engine.load_accompaniment(path, on_extracted)

    def toggle_recording(self):
        if not self.engine.is_recording:
            # 1. Preparar Video (Pausar y resetear)
            self.media_player.pause()
            self.media_player.setPosition(0)
            
            # 2. Iniciar el motor de audio primero para que esté listo para recibir el trigger
            self.engine.start_recording()
            
            # 3. Disparar Video inmediatamente después
            # Usamos un pequeño delay técnico opcional si detectamos que el player es lento,
            # pero por ahora el orden Engine -> Player es más estable para evitar perder audio.
            self.media_player.play()
            
            self.btn_record.setText("Detener")
            self.btn_record.setProperty("recording", "true")
            self.btn_record.style().unpolish(self.btn_record)
            self.btn_record.style().polish(self.btn_record)
            self.status_label.setText("CANTANDO...")
        else:
            self.media_player.stop()
            self.engine.stop_recording()
            
            self.btn_record.setText("Grabar")
            self.btn_record.setProperty("recording", "false")
            self.btn_record.style().unpolish(self.btn_record)
            self.btn_record.style().polish(self.btn_record)
            self.status_label.setText("Grabación finalizada.")
            
            # Abrir ventana de reproducción
            self.open_playback()

    def open_playback(self):
        self.playback_window = PlaybackWindow(self.engine)
        self.playback_window.show()

    def toggle_monitor(self):
        is_on = self.btn_monitor.isChecked()
        self.engine.is_monitoring = is_on
        self.btn_monitor.setText(f"Monitoreo: {'ON' if is_on else 'OFF'}")

    def closeEvent(self, event):
        self.engine.stop()
        self.engine.cleanup_temporary_files()
        event.accept()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
