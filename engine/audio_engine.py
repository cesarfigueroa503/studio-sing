import numpy as np
import sounddevice as sd
from scipy import signal
import threading
import queue
import os
from datetime import datetime
import soundfile as sf
from PySide6.QtMultimedia import QAudioDecoder
from PySide6.QtCore import QUrl, QObject, Signal

class AudioExtractor(QObject):
    finished = Signal(np.ndarray)
    error = Signal(str)

    def __init__(self, file_path, target_sample_rate):
        super().__init__()
        self.file_path = file_path
        self.target_sample_rate = target_sample_rate
        self.decoder = QAudioDecoder()
        self.decoder.setSource(QUrl.fromLocalFile(file_path))
        self.decoder.bufferReady.connect(self._on_buffer_ready)
        self.decoder.finished.connect(self._on_finished)
        self.decoder.error.connect(self._on_error)
        self.samples = []
        self.source_sample_rate = 0

    def start(self):
        self.samples = []
        self.decoder.start()

    def _on_buffer_ready(self):
        buffer = self.decoder.read()
        if self.source_sample_rate == 0:
            self.source_sample_rate = buffer.format().sampleRate()
            
        ptr = buffer.constData()
        count = buffer.sampleCount()
        
        if buffer.format().sampleFormat() == buffer.format().SampleFormat.Float:
            data = np.frombuffer(ptr, dtype=np.float32, count=count)
        else:
            data = np.frombuffer(ptr, dtype=np.int16, count=count).astype(np.float32) / 32768.0
        
        if buffer.format().channelCount() == 2:
            data = (data[0::2] + data[1::2]) / 2.0
            
        self.samples.append(data)

    def _on_finished(self):
        if self.samples:
            full_data = np.concatenate(self.samples)
            
            # RESAMPLING: Crucial para evitar desincronización
            if self.source_sample_rate != self.target_sample_rate and self.source_sample_rate > 0:
                print(f"Resampleando de {self.source_sample_rate}Hz a {self.target_sample_rate}Hz...")
                gcd = np.gcd(int(self.source_sample_rate), int(self.target_sample_rate))
                up = self.target_sample_rate // gcd
                down = self.source_sample_rate // gcd
                full_data = signal.resample_poly(full_data, up, down)
                
            self.finished.emit(full_data)
        else:
            self.error.emit("No se extrajeron samples.")

    def _on_error(self, error):
        self.error.emit(f"Error de decodificación: {error}")

class AudioEngine:
    def __init__(self, sample_rate=44100, block_size=128):
        self.sample_rate = sample_rate
        self.block_size = block_size
        
        self.input_device, self.output_device = self._find_best_devices()
        
        # Parámetros de efectos (SciPy)
        self.hp_freq = 80  
        self.lp_freq = 15000 
        self.bass_gain = 0  # dB
        self.treble_gain = 0 # dB
        
        # Coeficientes y estados pre-calculados
        self._update_basic_filters()
        
        # Efectos de Tiempo (Echo)
        self.echo_mix = 0.0
        self.echo_feedback = 0.4
        self.echo_delay_sec = 0.3
        self.b_echo = self.a_echo = self.zi_echo = None
        self._update_echo_params()
        
        # Efectos de Tiempo (Reverb)
        self.reverb_mix = 0.0
        self.rev_delays = [0.029, 0.037, 0.043, 0.049]
        self.rev_gain = 0.7
        self.rev_filters = [] 
        self._update_reverb_params()
        
        # --- Parámetros de Karaoke ---
        self.accompaniment_data = None 
        self.voice_volume = 1.0
        self.accompaniment_volume = 0.5
        self.monitoring_volume = 1.0 
        self.latency_offset_ms = 0 
        self.base_latency_ms = 150 # Compensación base para el retardo del reproductor de video
        self.accompaniment_path = ""
        
        self.stream = None
        self.playback_stream = None
        self.is_monitoring = False # Cambiado: empieza apagado
        self.is_recording = False
        self.is_previewing = False
        self.is_paused = False
        
        self.recording_queue = queue.Queue()
        self.recording_thread = None
        self.current_filename = ""
        self.last_recorded_file = ""

    def _find_best_devices(self):
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        wasapi_idx = next((i for i, api in enumerate(hostapis) if "WASAPI" in api['name']), -1)
        in_idx, out_idx = None, None
        if wasapi_idx != -1:
            for i, dev in enumerate(devices):
                if dev['hostapi'] == wasapi_idx:
                    if dev['max_input_channels'] > 0 and in_idx is None: in_idx = i
                    if dev['max_output_channels'] > 0 and out_idx is None: out_idx = i
        return in_idx, out_idx

    def _update_basic_filters(self):
        self.b_hp, self.a_hp = signal.butter(2, self.hp_freq, 'hp', fs=self.sample_rate)
        self.zi_hp = None 
        self.b_lp, self.a_lp = signal.butter(2, self.lp_freq, 'lp', fs=self.sample_rate)
        self.zi_lp = None
        self.b_bass, self.a_bass = signal.butter(1, 200, 'lp', fs=self.sample_rate)
        self.zi_bass = None
        self.b_treble, self.a_treble = signal.butter(1, 4000, 'hp', fs=self.sample_rate)
        self.zi_treble = None

    def _update_echo_params(self):
        delay_samples = int(self.sample_rate * self.echo_delay_sec)
        self.b_echo = np.zeros(delay_samples + 1); self.b_echo[delay_samples] = 1.0
        self.a_echo = np.zeros(delay_samples + 1); self.a_echo[0] = 1.0; self.a_echo[delay_samples] = -self.echo_feedback
        self.zi_echo = np.zeros((delay_samples, 1))

    def _update_reverb_params(self):
        self.rev_filters = []
        for d_sec in self.rev_delays:
            d_samples = int(self.sample_rate * d_sec)
            b = np.zeros(d_samples + 1); b[d_samples] = 1.0
            a = np.zeros(d_samples + 1); a[0] = 1.0; a[d_samples] = -self.rev_gain
            zi = np.zeros((d_samples, 1))
            self.rev_filters.append({'b': b, 'a': a, 'zi': zi})

    def load_accompaniment(self, file_path, callback=None):
        self.accompaniment_path = file_path
        self.extractor = AudioExtractor(file_path, self.sample_rate)
        
        def on_finished(data):
            self.accompaniment_data = data
            if callback: callback(True)
            
        def on_error(msg):
            print(f"Error al cargar acompañamiento: {msg}")
            if callback: callback(False)
            
        self.extractor.finished.connect(on_finished)
        self.extractor.error.connect(on_error)
        self.extractor.start()

    def callback(self, indata, outdata, frames, time, status):
        if self.is_recording:
            self.recording_queue.put(indata.copy())
            
        # Generar salida (Solo Monitoreo de Voz)
        out_res = np.zeros((frames, 1))
        
        # 1. Añadir monitoreo de voz si está activo
        if self.is_monitoring:
            out_res += indata * self.monitoring_volume
            
        outdata[:] = np.clip(out_res, -1.0, 1.0)

    def start(self):
        try:
            device_info = sd.query_devices(self.input_device if self.input_device is not None else sd.default.device[0], 'input')
            self.sample_rate = int(device_info['default_samplerate'])
            self._update_basic_filters()
            self._update_echo_params()
            self._update_reverb_params()
            
            self.stream = sd.Stream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                device=(self.input_device, self.output_device),
                channels=1,
                latency='low',
                callback=self.callback
            )
            self.stream.start()
        except Exception as e:
            print(f"Error: {e}")

    def start_recording(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_filename = f"recordings/raw_{timestamp}.wav"
        if not os.path.exists("recordings"):
            os.makedirs("recordings")
        self.is_recording = True
        self._rec_frames_ptr = 0 # Resetear puntero de pista para grabar desde el inicio
        self.recording_queue = queue.Queue()
        self.recording_thread = threading.Thread(target=self._recording_worker)
        self.recording_thread.start()

    def stop_recording(self):
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join()
        self.last_recorded_file = self.current_filename
        return self.last_recorded_file

    def _recording_worker(self):
        with sf.SoundFile(self.current_filename, mode='x', samplerate=self.sample_rate, channels=1) as f:
            while self.is_recording or not self.recording_queue.empty():
                try:
                    data = self.recording_queue.get(timeout=0.1)
                    f.write(data)
                except queue.Empty: continue

    def apply_scipy_filters(self, data):
        # 1. Aplicar filtros (Reducción de ruido eliminada)
        res = data.copy()
        
        channels = res.shape[1]
        if self.zi_hp is None: self.zi_hp = np.tile(signal.lfilter_zi(self.b_hp, self.a_hp), (channels, 1)).T
        res, self.zi_hp = signal.lfilter(self.b_hp, self.a_hp, res, axis=0, zi=self.zi_hp)
        if self.zi_lp is None: self.zi_lp = np.tile(signal.lfilter_zi(self.b_lp, self.a_lp), (channels, 1)).T
        res, self.zi_lp = signal.lfilter(self.b_lp, self.a_lp, res, axis=0, zi=self.zi_lp)
        if self.bass_gain != 0:
            gain_linear = (10**(self.bass_gain/20)) - 1
            if self.zi_bass is None: self.zi_bass = np.tile(signal.lfilter_zi(self.b_bass, self.a_bass), (channels, 1)).T
            bass_comp, self.zi_bass = signal.lfilter(self.b_bass, self.a_bass, res, axis=0, zi=self.zi_bass)
            res = res + (bass_comp * gain_linear)
        if self.treble_gain != 0:
            gain_linear = (10**(self.treble_gain/20)) - 1
            if self.zi_treble is None: self.zi_treble = np.tile(signal.lfilter_zi(self.b_treble, self.a_treble), (channels, 1)).T
            treble_comp, self.zi_treble = signal.lfilter(self.b_treble, self.a_treble, res, axis=0, zi=self.zi_treble)
            res = res + (treble_comp * gain_linear)
        if self.echo_mix > 0:
            echo_out, self.zi_echo = signal.lfilter(self.b_echo, self.a_echo, res, axis=0, zi=self.zi_echo)
            res = (res * (1.0 - self.echo_mix)) + (echo_out * self.echo_mix)
        if self.reverb_mix > 0:
            rev_total = np.zeros_like(res)
            for f in self.rev_filters:
                comb_out, f['zi'] = signal.lfilter(f['b'], f['a'], res, axis=0, zi=f['zi'])
                rev_total += comb_out
            res = (res * (1.0 - self.reverb_mix)) + ((rev_total / 4.0) * self.reverb_mix)
        return np.clip(res * self.voice_volume, -1.0, 1.0)

    def start_preview(self, restart=False):
        if not self.last_recorded_file: return
        if self.is_previewing and not restart: return
        self.stop_playback()
        self.is_previewing = True
        self.is_paused = False
        self.preview_data, _ = sf.read(self.last_recorded_file)
        if self.preview_data.ndim == 1: self.preview_data = self.preview_data.reshape(-1, 1)
        self.last_pos = 0
        self._update_basic_filters()
        self._update_echo_params()
        self._update_reverb_params()
        
        def preview_callback(outdata, frames, time, status):
            if self.is_paused:
                outdata[:] = 0
                return
            chunk_voice = self.preview_data[self.last_pos:self.last_pos+frames]
            voice_res = np.zeros((frames, 1))
            if len(chunk_voice) > 0: voice_res[:len(chunk_voice), :] = chunk_voice
            processed_voice = self.apply_scipy_filters(voice_res)
            final_res = processed_voice
            if self.accompaniment_data is not None:
                offset_samples = int((self.latency_offset_ms / 1000.0) * self.sample_rate)
                acc_pos = self.last_pos + offset_samples
                if acc_pos < len(self.accompaniment_data):
                    start_in_acc = max(0, acc_pos)
                    end_in_acc = min(len(self.accompaniment_data), acc_pos + frames)
                    if end_in_acc > start_in_acc:
                        data_acc = self.accompaniment_data[acc_pos:acc_pos+frames] # Simplificado para evitar errores de slice
                        # Asegurar que el acompañamiento tenga el mismo tamaño que el chunk de voz
                        acc_payload = np.zeros((frames, 1))
                        copy_len = min(len(data_acc), frames)
                        acc_payload[:copy_len, 0] = data_acc[:copy_len]
                        final_res = final_res + (acc_payload * self.accompaniment_volume)
            outdata[:] = np.clip(final_res, -1.0, 1.0)
            self.last_pos += frames
            if self.last_pos >= len(self.preview_data) and (self.accompaniment_data is None or self.last_pos >= len(self.accompaniment_data)):
                 raise sd.CallbackStop

        self.playback_stream = sd.OutputStream(
            samplerate=self.sample_rate,
            device=self.output_device,
            channels=1,
            callback=preview_callback,
            finished_callback=self._preview_finished
        )
        self.playback_stream.start()

    def toggle_pause_preview(self):
        self.is_paused = not self.is_paused
        return self.is_paused

    def seek_preview(self, position_seconds):
        if not hasattr(self, 'preview_data'): return
        self.last_pos = int(max(0, min(position_seconds * self.sample_rate, len(self.preview_data))))

    def get_playback_info(self):
        if not hasattr(self, 'preview_data'): return 0, 0
        total_time = len(self.preview_data) / self.sample_rate
        if self.accompaniment_data is not None:
            total_time = max(total_time, len(self.accompaniment_data) / self.sample_rate)
        return self.last_pos / self.sample_rate, total_time

    def _preview_finished(self):
        self.is_previewing = False

    def set_noise_filters(self, hp, lp):
        self.hp_freq, self.lp_freq = hp, lp
        self._update_basic_filters()

    def set_studio_eq(self, bass, treble):
        self.bass_gain, self.treble_gain = bass, treble
        self.zi_bass = self.zi_treble = None

    def set_echo(self, mix):
        self.echo_mix = mix
        self._update_echo_params()

    def set_reverb(self, mix):
        self.reverb_mix = mix
        self._update_reverb_params()

    def save_final_generator(self, output_path):
        if not self.last_recorded_file: return
        self._update_basic_filters()
        self._update_echo_params()
        self._update_reverb_params()

        with sf.SoundFile(self.last_recorded_file) as f_voice:
            sr = f_voice.samplerate
            # La duración final la manda la voz grabada
            total_frames = len(f_voice)
            
            with sf.SoundFile(output_path, mode='w', samplerate=sr, channels=1) as f_out:
                chunk_size = 1024 * 16
                frames_processed = 0
                
                while frames_processed < total_frames:
                    # 1. Leer Voz (Esencial)
                    chunk_voice = f_voice.read(chunk_size)
                    if len(chunk_voice) == 0: break
                    if chunk_voice.ndim == 1: chunk_voice = chunk_voice.reshape(-1, 1)
                    
                    processed_voice = self.apply_scipy_filters(chunk_voice)
                    
                    # 2. Mezclar con Acompañamiento (Opcional, hasta donde dure la pista)
                    final_res = processed_voice
                    if self.accompaniment_data is not None:
                        # Leer solo el trozo correspondiente de la pista extraída
                        acc_start = frames_processed
                        acc_end = min(len(self.accompaniment_data), frames_processed + len(chunk_voice))
                        
                        if acc_start < len(self.accompaniment_data):
                            chunk_acc = self.accompaniment_data[acc_start:acc_end]
                            # Si la pista es más corta que el chunk de voz, rellenar con ceros
                            acc_payload = np.zeros((len(chunk_voice), 1))
                            acc_payload[:len(chunk_acc), 0] = chunk_acc
                            final_res = final_res + (acc_payload * self.accompaniment_volume)
                    
                    f_out.write(np.clip(final_res, -1.0, 1.0))
                    frames_processed += len(chunk_voice)
                    yield frames_processed / total_frames

    def save_final(self, output_path):
        for _ in self.save_final_generator(output_path): pass

    def stop_playback(self):
        if self.playback_stream:
            self.playback_stream.stop()
            self.playback_stream.close()
            self.playback_stream = None
        self.is_previewing = False

    def cleanup_temporary_files(self):
        if os.path.exists("recordings"):
            for filename in os.listdir("recordings"):
                if filename.startswith("raw_") and filename.endswith(".wav"):
                    try: os.remove(os.path.join("recordings", filename))
                    except: pass

    def stop(self):
        if self.stream: self.stream.stop()
        self.stop_playback()
