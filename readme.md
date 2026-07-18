# WeFax Encoder v2 (120 LPM / IOC 576)

Un codificador de imágenes analógicas a audio en formato HF-FAX (WEFAX) desarrollado en Python. Permite transformar mapas meteorológicos, imágenes satelitales o fotografías en señales de audio moduladas en frecuencia (FM) listas para ser transmitidas por radio o cables de audio virtuales.

## 🚀 Características de la versión 2

- **Soporte de Formatos Ampliado:** Carga imágenes en formato `.png`, `.jpg`, `.jpeg` y formatos profesionales de mapas climáticos como `.tiff` y `.tif`.
- **Selector de Tarjeta de Sonido Integrado:** Menú desplegable para elegir en tiempo real la salida de audio (`sounddevice`), permitiendo rutear el audio directo a altavoces, transmisores o cables virtuales (ej. VB-Cable) sin congelar la interfaz.
- **Estándar Internacional:** Modulación fija a 120 LPM (Lines Per Minute) con un IOC (Index of Cooperation) de 576.
- **Interfaz Moderna:** Diseño oscuro optimizado para no cansar la vista durante operaciones nocturnas de radio.

## 🛠️ Requisitos e Instalación

Asegúrate de tener Python 3 instalado en tu sistema (Windows o Linux) junto con las siguientes dependencias:

```bash
pip install numpy scipy pillow sounddevice