# Grabadora de Voz Limpia (Karaoke Project)

Aplicación de escritorio para Windows diseñada para la grabación de voz y monitoreo en tiempo real con baja latencia. El sistema está optimizado para capturar "voz limpia" (sin efectos), ideal para sesiones de grabación profesionales o práctica de karaoke.

## Características

- **Monitoreo en Tiempo Real**: Escucha tu voz mientras grabas sin retrasos perceptibles.
- **Grabación de Alta Fidelidad**: Captura de audio utilizando `sounddevice` y almacenamiento en formato `.wav`.
- **Interfaz Moderna**: UI construida con PySide6 con soporte nativo para tema oscuro.
- **Arquitectura Robusta**: Manejo de hilos separado para la interfaz y el motor de audio, garantizando estabilidad durante la grabación.

## Stack Tecnológico

- **Lenguaje**: Python 3.14+
- **Interfaz Gráfica**: PySide6 (Qt for Python)
- **Motor de Audio**: Sounddevice
- **Procesamiento de Datos**: NumPy
- **Formatos de Audio**: Soundfile

## Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación.
- `engine/`: Lógica del motor de audio y gestión de buffers.
- `ui/`: Archivos de la interfaz de usuario (ventanas y componentes).
- `recordings/`: Directorio donde se almacenan las grabaciones (ignorado por git).
- `models/`: Directorio para posibles modelos de datos futuros.

## Requisitos Previos

Asegúrate de tener instalado Python 3.14 o superior. Puedes verificar tu versión con:
```powershell
python --version
```

## Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/cesarfigueroa503/studio-sing.git
   cd karaoke-project
   ```

2. **Crear un entorno virtual (recomendado)**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Instalar dependencias**:
   ```powershell
   pip install PySide6 sounddevice numpy soundfile
   ```

## Ejecución

Para iniciar la aplicación, simplemente ejecuta el script principal:

```powershell
python main.py
```

## Cómo Colaborar

Las contribuciones son bienvenidas. Para colaborar:

1. Realiza un **Fork** del proyecto.
2. Crea una nueva rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus cambios y haz **Commit** (`git commit -m 'Añade nueva funcionalidad'`).
4. Haz **Push** a la rama (`git push origin feature/nueva-funcionalidad`).
5. Abre un **Pull Request**.

## Licencia

Este proyecto es de uso personal/educativo. Revisa los archivos de código para más detalles sobre la autoría.
