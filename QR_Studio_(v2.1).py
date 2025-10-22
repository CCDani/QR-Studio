import sys
import os
import io
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QColor, QImageReader, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QTextEdit, QComboBox, QCheckBox, QSpinBox,
    QColorDialog, QFileDialog, QSizePolicy, QFrame, QStatusBar, QMessageBox,
    QLineEdit, QSlider 
)

# Importaciones específicas de qrcode
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer, RoundedModuleDrawer, CircleModuleDrawer
)
from qrcode.image.styles.colormasks import SolidFillColorMask

from PIL import Image, ImageDraw, ImageFont

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QR-Studio 🎨 v2.1")
        self.setGeometry(100, 100, 1000, 700) # Un poco más alto para la nueva opción

        # --- Variables de estado ---
        self.fill_color = (0, 0, 0)
        self.back_color = (255, 255, 255)
        self.logo_path = None
        self.current_qr_image = None
        self.current_pixmap = None
        self.initial_qr_generated = False

        # --- Diccionarios (sin cambios) ---
        self.module_drawers = {
            "Cuadrado": SquareModuleDrawer(),
            "Redondeado": RoundedModuleDrawer(radius_ratio=1.0),
            "Círculo": CircleModuleDrawer(),
        }
        self.error_correction = {
            "Baja (L)": qrcode.constants.ERROR_CORRECT_L,
            "Media (M)": qrcode.constants.ERROR_CORRECT_M,
            "Cuartil (Q)": qrcode.constants.ERROR_CORRECT_Q,
            "Alta (H)": qrcode.constants.ERROR_CORRECT_H
        }

        # --- Configurar la UI ---
        self.init_ui()
        
        # --- 1. Poner textos por defecto ANTES de conectar ---
        self.text_input.setText("https://www.google.com/")
        self.description_input.setText("QR-Studio")

        # --- 2. Conectar todas las señales ---
        self.connect_signals()
        
        # 3. La generación inicial se hará en showEvent()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        options_panel = self.create_options_panel()
        main_layout.addWidget(options_panel, 1)

        preview_panel = self.create_preview_panel()
        main_layout.addWidget(preview_panel, 2)

        content_panel = self.create_content_panel()
        main_layout.addWidget(content_panel, 1)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Listo.")

    # --- Creación de Paneles ---

    def create_options_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)

        # --- Colores ---
        layout.addWidget(QLabel("<b>Colores</b>"))
        self.fill_color_button = QPushButton("Color de Módulos (Negro)")
        self.back_color_button = QPushButton("Color de Fondo (Blanco)")
        layout.addWidget(self.fill_color_button)
        layout.addWidget(self.back_color_button)

        # --- Estilo de Módulos ---
        layout.addWidget(QLabel("<b>Estilo de Módulos</b>"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(self.module_drawers.keys())
        layout.addWidget(self.style_combo)

        # --- Logo (¡ORDEN CORREGIDO!) ---
        layout.addWidget(QLabel("<b>Logo</b>"))
        self.logo_check = QCheckBox("Añadir Logo")
        self.logo_button = QPushButton("Buscar Logo...")
        self.logo_label = QLabel("No hay logo seleccionado.")
        self.logo_label.setWordWrap(True)
        
        layout.addWidget(self.logo_check) # 1. Checkbox
        layout.addWidget(self.logo_button) # 2. Botón
        layout.addWidget(self.logo_label) # 3. Etiqueta de archivo

        # Tamaño del Logo (Slider)
        layout.addWidget(QLabel("Tamaño del Logo:")) # 4. Etiqueta del slider
        slider_layout = QHBoxLayout()
        self.logo_size_slider = QSlider(Qt.Horizontal)
        self.logo_size_slider.setMinimum(10) # 10%
        self.logo_size_slider.setMaximum(50) # 50%
        self.logo_size_slider.setValue(25)   # 25% por defecto
        self.logo_size_label = QLabel(" 25 %") # Muestra el %
        slider_layout.addWidget(self.logo_size_slider) # 5. Slider
        slider_layout.addWidget(self.logo_size_label)
        layout.addLayout(slider_layout) # 6. Añadir el layout del slider

        # Deshabilitar controles de logo por defecto
        self.logo_button.setEnabled(False)
        self.logo_size_slider.setEnabled(False)
        self.logo_size_label.setEnabled(False)
        
        # --- Avanzado ---
        layout.addWidget(QLabel("<b>Avanzado</b>"))
        layout.addWidget(QLabel("Corrección de Error:"))
        self.error_combo = QComboBox()
        self.error_combo.addItems(self.error_correction.keys())
        self.error_combo.setCurrentText("Alta (H)")
        layout.addWidget(self.error_combo)

        layout.addWidget(QLabel("Tamaño de Módulo (px):"))
        self.box_spin = QSpinBox()
        self.box_spin.setValue(10)
        self.box_spin.setMinimum(1)
        layout.addWidget(self.box_spin)

        layout.addWidget(QLabel("Tamaño del Borde:"))
        self.border_spin = QSpinBox()
        self.border_spin.setValue(4)
        self.border_spin.setMinimum(0)
        layout.addWidget(self.border_spin)

        # --- ¡NUEVO! Sección de Radio de Borde ---
        layout.addWidget(QLabel("Estilo de Borde (px):"))
        border_radius_layout = QHBoxLayout()
        self.border_radius_slider = QSlider(Qt.Horizontal)
        self.border_radius_slider.setMinimum(0)
        self.border_radius_slider.setMaximum(100) # Radio en píxeles
        self.border_radius_slider.setValue(0)
        self.border_radius_label = QLabel(" 0 px")
        border_radius_layout.addWidget(self.border_radius_slider)
        border_radius_layout.addWidget(self.border_radius_label)
        layout.addLayout(border_radius_layout)
        
        layout.addStretch()
        return panel

    def create_preview_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignCenter)

        self.qr_preview_label = QLabel()
        self.qr_preview_label.setAlignment(Qt.AlignCenter)
        self.qr_preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.qr_preview_label.setScaledContents(False)
        self.qr_preview_label.setMinimumSize(400, 400)
        layout.addWidget(self.qr_preview_label)
        
        return panel

    def create_content_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("<b>URL o Texto a codificar</b>"))
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Escribe aquí tu URL, texto, datos de WiFi, etc.")
        self.text_input.setMinimumHeight(150)
        layout.addWidget(self.text_input, 1)

        layout.addWidget(QLabel("<b>Descripción (opcional)</b>"))
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Ej: Carta de Telepizza")
        layout.addWidget(self.description_input)
        
        layout.addWidget(QLabel("<b>Acciones</b>"))
        self.save_button = QPushButton("Guardar QR como...")
        self.copy_button = QPushButton("Copiar al Portapapeles")
        self.reset_button = QPushButton("Restablecer Opciones")
        
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.reset_button.setStyleSheet("background-color: #f44336; color: white;")
        
        layout.addWidget(self.save_button)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.reset_button)
        
        return panel

    # --- Lógica de Conexiones ---

    def connect_signals(self):
        # Widgets que regeneran el QR
        self.text_input.textChanged.connect(self.generate_qr_preview)
        self.style_combo.currentTextChanged.connect(self.generate_qr_preview)
        self.error_combo.currentTextChanged.connect(self.generate_qr_preview)
        self.box_spin.valueChanged.connect(self.generate_qr_preview)
        self.border_spin.valueChanged.connect(self.generate_qr_preview)
        self.description_input.textChanged.connect(self.generate_qr_preview)
        
        # Botones de color
        self.fill_color_button.clicked.connect(self.open_fill_color_dialog)
        self.back_color_button.clicked.connect(self.open_back_color_dialog)
        
        # Conexiones de Logo
        self.logo_check.toggled.connect(self.on_logo_toggled)
        self.logo_button.clicked.connect(self.open_logo_file)
        self.logo_size_slider.valueChanged.connect(self.on_logo_slider_change)

        # --- Conexión de Radio de Borde ---
        self.border_radius_slider.valueChanged.connect(self.on_border_radius_change)

        # Botones de acción
        self.save_button.clicked.connect(self.save_qr)
        self.copy_button.clicked.connect(self.copy_qr)
        self.reset_button.clicked.connect(self.reset_options)

    # --- Función Central de Generación ---

    def generate_qr_preview(self):
        data = self.text_input.toPlainText()
        description_text = self.description_input.text()

        if not data:
            self.qr_preview_label.clear()
            self.current_qr_image = None
            self.current_pixmap = None
            return

        try:
            # 1. Generar la imagen QR base
            qr = qrcode.QRCode(
                version=1,
                error_correction=self.error_correction[self.error_combo.currentText()],
                box_size=self.box_spin.value(),
                border=self.border_spin.value(),
            )
            qr.add_data(data)
            qr.make(fit=True)

            selected_drawer = self.module_drawers[self.style_combo.currentText()]
            color_mask = SolidFillColorMask(front_color=self.fill_color, back_color=self.back_color)

            qr_image = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=selected_drawer,
                color_mask=color_mask
            ).convert("RGBA")

            # 2. Añadir el logo (si está activado)
            if self.logo_check.isChecked() and self.logo_path:
                qr_image = self.embed_logo(qr_image)

            # 3. Crear lienzo final y añadir descripción
            final_image = self.add_description_to_image(qr_image, description_text)

            # 4. Aplicar radio de borde ---
            border_radius_val = self.border_radius_slider.value()
            if border_radius_val > 0:
                final_image = self.apply_border_radius(final_image, border_radius_val)

            # 5. Almacenar la imagen PIL final
            self.current_qr_image = final_image

            # 6. Convertir a QPixmap y ALMACENAR
            buffer = io.BytesIO()
            final_image.save(buffer, "PNG")
            self.current_pixmap = QPixmap()
            self.current_pixmap.loadFromData(buffer.getvalue())

            # 7. Llamar a la función separada para MOSTRAR
            self.update_preview_display()
            
            self.statusBar().showMessage("Vista previa actualizada.", 2000)

        except Exception as e:
            self.statusBar().showMessage(f"Error al generar QR: {e}")
            self.current_pixmap = None
            self.update_preview_display()

    # --- Función para aplicar radio de borde ---
    def apply_border_radius(self, image, radius):
        """
        Aplica un radio de borde a la imagen final usando una máscara.
        """
        try:
            # Crear una máscara alfa (L = 8-bit pixels, black and white)
            mask = Image.new("L", image.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0) + image.size, radius=radius, fill=255)
            
            # Crear la imagen de salida transparente
            rounded_img = Image.new("RGBA", image.size, (0, 0, 0, 0))
            # Pegar la imagen original usando la máscara
            rounded_img.paste(image, (0, 0), mask=mask)
            
            return rounded_img
        except Exception as e:
            self.statusBar().showMessage(f"Error al redondear bordes: {e}", 2000)
            return image

    def add_description_to_image(self, qr_image, text):
        
        if not text or text.isspace():
            return qr_image 

        font_size = max(15, qr_image.width // 20)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            self.statusBar().showMessage("Fuente Arial no encontrada, usando fuente por defecto.", 1000)
            font = ImageFont.load_default()

        text_bbox = font.getbbox(text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        padding_top = 10    # Espacio entre QR y texto
        padding_bottom = 20 # Espacio entre texto y borde inferior

        new_width = qr_image.width
        new_height = qr_image.height + text_height + padding_top + padding_bottom
        
        final_image = Image.new("RGBA", (new_width, new_height), self.back_color)
        final_image.paste(qr_image, (0, 0))

        draw = ImageDraw.Draw(final_image)
        text_x = (new_width - text_width) // 2
        text_y = qr_image.height + padding_top
        
        draw.text((text_x, text_y), text, font=font, fill=self.fill_color)
        
        return final_image

    def embed_logo(self, qr_image):
        
        try:
            logo = Image.open(self.logo_path).convert("RGBA")

            qr_width, qr_height = qr_image.size
            
            logo_ratio = self.logo_size_slider.value() / 100.0
            logo_max_size = int(qr_height * logo_ratio)
            logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)

            box_x = (qr_width - logo.width) // 2
            box_y = (qr_height - logo.height) // 2
            pos = (box_x, box_y)

            qr_image.paste(logo, pos, mask=logo)
            return qr_image
            
        except Exception as e:
            self.statusBar().showMessage(f"Error al cargar el logo: {e}", 3000)
            self.logo_check.setChecked(False)
            return qr_image

    # --- Funciones de los Widgets ---

    def open_fill_color_dialog(self):
        color = QColorDialog.getColor(QColor(*self.fill_color))
        if color.isValid():
            self.fill_color = color.getRgb()[:3]
            self.fill_color_button.setText(f"Color de Módulos ({color.name()})")
            self.generate_qr_preview()

    def open_back_color_dialog(self):
        color = QColorDialog.getColor(QColor(*self.back_color))
        if color.isValid():
            self.back_color = color.getRgb()[:3]
            self.back_color_button.setText(f"Color de Fondo ({color.name()})")
            self.generate_qr_preview()

    def on_logo_toggled(self, checked):
        # (Función simplificada, sin cambios)
        self.logo_button.setEnabled(checked)
        self.logo_size_slider.setEnabled(checked)
        self.logo_size_label.setEnabled(checked)

        if checked:
            self.error_combo.setCurrentText("Alta (H)")
            if not self.logo_path:
                self.open_logo_file()
            else:
                self.generate_qr_preview()
        else:
            self.generate_qr_preview()

    def on_logo_slider_change(self, value):
        self.logo_size_label.setText(f" {value} %")
        self.generate_qr_preview()
    
    # --- ¡NUEVO! Handler para el slider de radio de borde ---
    def on_border_radius_change(self, value):
        self.border_radius_label.setText(f" {value} px")
        self.generate_qr_preview()

    def open_logo_file(self):
        supported_formats = " ".join([f"*.{fmt.data().decode()}" for fmt in QImageReader.supportedImageFormats()])
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Logo", "", f"Imágenes ({supported_formats});;Todos los archivos (*)"
        )
        if path:
            self.logo_path = path
            self.logo_label.setText(os.path.basename(path))
            self.logo_check.setChecked(True)
            self.generate_qr_preview()

    def save_qr(self):
        if not self.current_qr_image:
            QMessageBox.warning(self, "Nada que guardar", "Primero genera un código QR.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Código QR", "mi_codigo_qr.png", "PNG (*.png);;JPEG (*.jpg)"
        )
        
        if path:
            try:
                if path.lower().endswith(('.jpg', '.jpeg')):
                    img_to_save = Image.new("RGB", self.current_qr_image.size, "WHITE")
                    img_to_save.paste(self.current_qr_image, (0, 0), self.current_qr_image)
                else:
                    # Si es PNG, guarda con transparencia
                    img_to_save = self.current_qr_image
                    
                img_to_save.save(path)
                self.statusBar().showMessage(f"¡QR guardado en {path}!", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

    def copy_qr(self):
        if not self.current_pixmap:
            QMessageBox.warning(self, "Nada que copiar", "Primero genera un código QR.")
            return
            
        clipboard = QGuiApplication.clipboard()
        clipboard.setPixmap(self.current_pixmap)
        self.statusBar().showMessage("¡QR copiado al portapapeles!", 3000)

    def reset_options(self):
        self.fill_color = (0, 0, 0)
        self.back_color = (255, 255, 255)
        self.logo_path = None
        
        self.fill_color_button.setText("Color de Módulos (Negro)")
        self.back_color_button.setText("Color de Fondo (Blanco)")
        
        self.style_combo.setCurrentIndex(0)
        self.error_combo.setCurrentText("Alta (H)")
        
        self.logo_check.setChecked(False)
        self.logo_label.setText("No hay logo seleccionado.")
        self.logo_size_slider.setValue(25)
        self.description_input.clear()
        
        self.box_spin.setValue(10)
        self.border_spin.setValue(4)
        
        # --- Resetear radio de borde ---
        self.border_radius_slider.setValue(0)
        
        self.text_input.setText("https://www.google.com/")
        self.description_input.setText("QR-Studio")
        
        self.statusBar().showMessage("Opciones restablecidas.", 3000)
        self.generate_qr_preview()

    # --- Funciones de Eventos (sin cambios) ---

    def update_preview_display(self):
        if not self.current_pixmap:
            self.qr_preview_label.clear()
            return
        
        self.qr_preview_label.setPixmap(self.current_pixmap.scaled(
            self.qr_preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))

    def showEvent(self, event):
        super().showEvent(event)
        if not self.initial_qr_generated:
            self.generate_qr_preview()
            self.initial_qr_generated = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview_display()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())