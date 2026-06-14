# Grabadora de Voz Limpia

Aplicación de escritorio para Windows diseñada para la grabación de voz y monitoreo en tiempo real sin efectos (voz limpia).

## Descripción del Proyecto
Este proyecto proporciona un entorno de grabación de audio profesional y simplificado. Utiliza librerías de alto rendimiento para asegurar baja latencia, capturando la voz tal cual se recibe del micrófono.

### Tecnologías Clave
- **Python 3.14+**: Lenguaje de programación principal.
- **PySide6 (Qt para Python)**: Framework para la interfaz de usuario moderna con tema oscuro.
- **Sounddevice**: Maneja flujos de entrada y salida de audio con baja latencia.
- **Soundfile / NumPy**: Utilizados para la manipulación y almacenamiento eficiente de buffers de audio.

### Arquitectura
- **`engine/`**: Contiene `AudioEngine`, que gestiona el flujo de audio, el hilo de grabación y la reproducción.
- **`ui/`**: Contiene la `MainWindow` y los componentes de la interfaz.
- **`recordings/`**: Directorio de almacenamiento por defecto para los archivos `.wav`.
- **`main.py`**: Punto de entrada de la aplicación, inicializa la UI y aplica estilos globales.

## Inicio Rápido

### Requisitos Previos
Asegúrate de tener Python 3.14 o superior instalado.

### Instalación
Instala las dependencias necesarias:
```powershell
pip install PySide6 sounddevice numpy soundfile
```

### Ejecutar la Aplicación
```powershell
python main.py
```

## Convenciones de Desarrollo

### Estructura del Código
- **Audio Limpio**: El sistema está diseñado para grabar y reproducir audio sin ningún tipo de procesamiento o efectos.
- **Seguridad de Hilos**: La grabación se maneja en un hilo de fondo dedicado utilizando una cola (`queue.Queue`) para no bloquear el callback de audio en tiempo real.
- **Baja Latencia**: El `block_size` está ajustado para un monitoreo estable y sin retrasos perceptibles.

### Estilo de la UI
La aplicación utiliza un tema oscuro definido en `main.py`. Se prioriza la simplicidad y la visibilidad de los controles de grabación.
