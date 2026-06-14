from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSlider, QFrame, QProgressBar,
                             QScrollArea, QToolButton, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
import threading

class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: #2e2e2e;
                color: white;
                font-weight: bold;
                padding: 10px;
                text-align: left;
                border-radius: 5px;
            }
            QToolButton:checked {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.clicked.connect(self.on_toggle)
        self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.content_area = QWidget()
        self.content_area.setStyleSheet("background-color: #1e1e1e; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;")
        self.content_area.hide()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)

    def on_toggle(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content_area.setVisible(checked)

    def set_layout(self, layout):
        self.content_area.setLayout(layout)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.label = QLabel("Calculando efectos de ambiente...")
        self.label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        layout.addWidget(self.label, 0, Qt.AlignCenter)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminado
        self.progress.setFixedWidth(200)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #388e3c;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #388e3c;
            }
        """)
        layout.addWidget(self.progress, 0, Qt.AlignCenter)
        
        self.hide()

    def show_loading(self):
        if self.parent():
            self.resize(self.parent().size())
        self.show()
        self.raise_()

class PlaybackWindow(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle("Edición y Reproducción de Voz")
        self.setMinimumSize(450, 450)
        self.setStyleSheet("background-color: #121212; color: white;")
        
        self.init_ui()
        
        # Overlay de carga
        self.loading_overlay = LoadingOverlay(self)
        
        # Iniciar reproducción automáticamente
        self.engine.start_preview()
        
        # Timer para actualizar la barra de progreso
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)
        
    def add_effect_control(self, label, min_v, max_v, default, callback, parent_layout):
        layout = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("border: none; color: #bbb;")
        layout.addWidget(lbl)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default)
        if callback:
            slider.valueChanged.connect(callback)
        layout.addWidget(slider)
        parent_layout.addLayout(layout)
        return slider

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Sección Fija de Reproducción (Superior) ---
        playback_frame = QFrame()
        playback_frame.setStyleSheet("background-color: #1e1e1e; border-radius: 10px;")
        playback_layout = QVBoxLayout(playback_frame)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        playback_layout.addWidget(self.time_label)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        playback_layout.addWidget(self.slider)
        
        controls_layout = QHBoxLayout()
        self.btn_backward = QPushButton("<< 5s")
        self.btn_play_pause = QPushButton("Pausar")
        self.btn_forward = QPushButton("5s >>")
        
        self.btn_backward.clicked.connect(lambda: self.seek(-5))
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_forward.clicked.connect(lambda: self.seek(5))
        
        controls_layout.addWidget(self.btn_backward)
        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addWidget(self.btn_forward)
        playback_layout.addLayout(controls_layout)
        
        main_layout.addWidget(playback_frame)

        # --- Área de Scroll para Controles ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 10, 0, 10)
        scroll_layout.setSpacing(10)
        
        # 1. Panel de Mezcla Karaoke
        if self.engine.accompaniment_data is not None:
            box_mix = CollapsibleBox("Mezcla de Karaoke")
            mix_layout = QVBoxLayout()
            self.voice_vol_slider = self.add_effect_control("Volumen de Voz", 0, 150, 100, mix_layout)
            self.music_vol_slider = self.add_effect_control("Volumen de Música", 0, 150, 50, mix_layout)
            self.voice_vol_slider.valueChanged.connect(lambda v: setattr(self.engine, 'voice_volume', v / 100.0))
            self.music_vol_slider.valueChanged.connect(lambda v: setattr(self.engine, 'accompaniment_volume', v / 100.0))
            box_mix.set_layout(mix_layout)
            scroll_layout.addWidget(box_mix)

        # 2. Panel de Limpieza de Audio
        box_clean = CollapsibleBox("Limpieza de Audio")
        clean_layout = QVBoxLayout()
        self.hp_slider = self.add_effect_control("Corte de Graves (Elimina zumbidos)", 20, 500, 80, clean_layout)
        self.lp_slider = self.add_effect_control("Corte de Agudos (Elimina siseo/hiss)", 5000, 20000, 15000, clean_layout)
        box_clean.set_layout(clean_layout)
        scroll_layout.addWidget(box_clean)

        # 3. Panel de Ecualización
        box_eq = CollapsibleBox("Ecualización de Estudio")
        eq_layout = QVBoxLayout()
        self.bass_slider = self.add_effect_control("Reforzar Graves (Voz profunda)", -10, 20, 0, eq_layout)
        self.treble_slider = self.add_effect_control("Brillo de Estudio (Voz clara)", -10, 20, 0, eq_layout)
        box_eq.set_layout(eq_layout)
        scroll_layout.addWidget(box_eq)

        # 4. Panel de Efectos de Tiempo
        box_fx = CollapsibleBox("Efectos de Ambiente")
        fx_layout = QVBoxLayout()
        self.echo_slider = self.add_effect_control("Eco (Eco Mix)", 0, 100, 0, fx_layout)
        self.reverb_slider = self.add_effect_control("Ambiente (Reverb Mix)", 0, 100, 0, fx_layout)
        box_fx.set_layout(fx_layout)
        scroll_layout.addWidget(box_fx)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # --- Conexiones de Filtros (Permanecen igual) ---
        self.hp_slider.sliderReleased.connect(lambda: self.apply_effect_with_loading(
            lambda: self.engine.set_noise_filters(self.hp_slider.value(), self.lp_slider.value())))
        self.lp_slider.sliderReleased.connect(lambda: self.apply_effect_with_loading(
            lambda: self.engine.set_noise_filters(self.hp_slider.value(), self.lp_slider.value())))
        self.bass_slider.sliderReleased.connect(lambda: self.apply_effect_with_loading(
            lambda: self.engine.set_studio_eq(self.bass_slider.value(), self.treble_slider.value())))
        self.treble_slider.sliderReleased.connect(lambda: self.apply_effect_with_loading(
            lambda: self.engine.set_studio_eq(self.bass_slider.value(), self.treble_slider.value())))
        self.echo_slider.sliderReleased.connect(lambda: self.apply_effect_with_loading(
            lambda: self.engine.set_echo(self.echo_slider.value() / 100.0)))
        self.reverb_slider.sliderReleased.connect(lambda: self.apply_effect_with_loading(
            lambda: self.engine.set_reverb(self.reverb_slider.value() / 100.0)))
        
        # Botón Exportar Final
        self.btn_export = QPushButton("Exportar Audio Editado (.WAV)")
        self.btn_export.setStyleSheet("background-color: #388e3c; font-weight: bold; min-height: 45px; margin-top: 10px;")
        self.btn_export.clicked.connect(self.export_edited)
        main_layout.addWidget(self.btn_export)

        self.is_dragging = False

    def add_effect_control(self, label, min_v, max_v, default, parent_layout):
        layout = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("border: none; color: #bbb;")
        layout.addWidget(lbl)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default)
        layout.addWidget(slider)
        parent_layout.addLayout(layout)
        return slider

    def apply_effect_with_loading(self, engine_callback):
        self.loading_overlay.show_loading()
        
        # Detener reproducción si está activa para evitar glitches
        was_playing = self.engine.is_previewing and not self.engine.is_paused
        if was_playing:
            self.engine.toggle_pause_preview()
            self.btn_play_pause.setText("Reproducir")

        def finish_processing():
            engine_callback()
            self.loading_overlay.hide()
            if was_playing:
                self.engine.toggle_pause_preview()
                self.btn_play_pause.setText("Pausar")

        # Tiempo de cálculo para estabilidad (se puede ajustar según la carga real)
        QTimer.singleShot(800, finish_processing)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(event.size())

    def toggle_play_pause(self):
        if not self.engine.is_previewing and not self.engine.is_paused:
            # Si el audio terminó (no está reproduciendo ni pausado), reiniciar
            self.engine.start_preview(restart=True)
            self.btn_play_pause.setText("Pausar")
        else:
            is_paused = self.engine.toggle_pause_preview()
            self.btn_play_pause.setText("Reproducir" if is_paused else "Pausar")

    def seek(self, seconds):
        curr, total = self.engine.get_playback_info()
        self.engine.seek_preview(curr + seconds)

    def on_slider_pressed(self):
        self.is_dragging = True

    def on_slider_released(self):
        self.is_dragging = False
        _, total = self.engine.get_playback_info()
        new_pos = (self.slider.value() / 1000.0) * total
        self.engine.seek_preview(new_pos)

    def update_progress(self):
        curr, total = self.engine.get_playback_info()
        if total > 0:
            if not self.is_dragging:
                self.slider.setValue(int((curr / total) * 1000))
            
            self.time_label.setText(f"{self.format_time(curr)} / {self.format_time(total)}")
        
        if not self.engine.is_previewing and not self.engine.is_paused:
            self.btn_play_pause.setText("Reproducir")
            self.slider.setValue(1000)

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def export_edited(self):
        from PySide6.QtWidgets import QFileDialog, QProgressDialog, QMessageBox
        from PySide6.QtCore import QCoreApplication
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Grabación Editada", "recordings/", "Audio Files (*.wav)")
        if not path:
            return

        # Configurar diálogo de progreso
        progress = QProgressDialog("Exportando audio editado...", "Cancelar", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.setStyleSheet("background-color: #1e1e1e; color: white;")
        progress.show()

        # Hilo para exportar sin bloquear la UI
        class ExportThread(threading.Thread):
            def __init__(self, engine, out_path, pd):
                super().__init__()
                self.engine = engine
                self.out_path = out_path
                self.pd = pd
                self.error = None
                self.success = False

            def run(self):
                try:
                    last_p = -1
                    for p in self.engine.save_final_generator(self.out_path):
                        prog_val = int(p * 100)
                        if prog_val > last_p:
                            last_p = prog_val
                            # Actualizar valor y forzar refresco visual en el hilo principal
                            QTimer.singleShot(0, lambda v=prog_val: self.pd.setValue(v))
                        
                        if self.pd.wasCanceled():
                            return
                    self.success = True
                except Exception as e:
                    self.error = str(e)

        thread = ExportThread(self.engine, path, progress)
        thread.start()

        # Timer para monitorear el hilo y cerrar el diálogo
        def check_thread():
            if not thread.is_alive():
                monitor_timer.stop()
                progress.close()
                if thread.error:
                    QMessageBox.critical(self, "Error", f"Error al exportar: {thread.error}")
                elif thread.success:
                    # QMessageBox.information(self, "Éxito", "Audio exportado correctamente.")
                    pass
            else:
                # Mantener la UI respondiendo
                QCoreApplication.processEvents()

        monitor_timer = QTimer(self)
        monitor_timer.timeout.connect(check_thread)
        monitor_timer.start(100)

    def closeEvent(self, event):
        self.engine.stop_playback() # Solo detener la reproducción al cerrar
        event.accept()
