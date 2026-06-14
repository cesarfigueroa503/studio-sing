import sys
from ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    
    # Aplicar un estilo oscuro profesional y moderno
    app.setStyleSheet("""
        QMainWindow { 
            background-color: #121212; 
        }
        
        QLabel { 
            color: #e0e0e0; 
            font-size: 14px; 
            font-weight: bold;
            margin: 5px;
        }
        
        /* Estilo base para todos los botones */
        QPushButton { 
            border-radius: 6px; 
            min-height: 40px; 
            min-width: 100px;
            font-size: 13px;
            font-weight: bold;
            color: white;
            background-color: #333333;
            border: 1px solid #444444;
            padding: 5px 15px;
        }
        
        QPushButton:hover {
            background-color: #444444;
            border: 1px solid #555555;
        }

        QPushButton:disabled {
            background-color: #1a1a1a;
            color: #555555;
            border: 1px solid #222222;
        }

        /* Botón de Grabar (Rojo) */
        QPushButton#btn_record {
            background-color: #d32f2f;
            border: none;
        }
        QPushButton#btn_record:hover {
            background-color: #f44336;
        }
        QPushButton#btn_record[recording="true"] {
            background-color: #212121;
            border: 2px solid #f44336;
        }

        /* Botón de Previsualizar (Azul) */
        QPushButton#btn_preview {
            background-color: #1976d2;
            border: none;
        }
        QPushButton#btn_preview:hover {
            background-color: #2196f3;
        }

        /* Botón de Guardar (Verde) */
        QPushButton#btn_save {
            background-color: #388e3c;
            border: none;
        }
        QPushButton#btn_save:hover {
            background-color: #4caf50;
        }

        /* Botón de Monitoreo (Toggle) */
        QPushButton#btn_monitor:checked {
            background-color: #fbc02d;
            color: black;
        }

        QFrame { 
            border: 1px solid #2c2c2c; 
            border-radius: 8px; 
            background-color: #1e1e1e; 
            margin: 4px; 
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
