import os
import platform
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Librerías matemáticas, de procesamiento de señales y audio
from PIL import Image
import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd  # Nueva librería para manejar tarjetas de sonido

# --- PARÁMETROS ESTÁNDAR WEFAX 120 / IOC 576 ---
SAMPLE_RATE = 11025      
LPM = 120                
F_CARRIER = 1900         
F_DEV = 400              
F_START = 300            
F_STOP = 450             
ANCHO_FAX = 1800         

def obtener_tarjetas_audio():
    """Obtiene la lista de nombres de dispositivos de salida de audio disponibles."""
    try:
        dispositivos = sd.query_devices()
        nombres_salidas = ["Predeterminado del Sistema"]
        for idx, dev in enumerate(dispositivos):
            if dev['max_output_channels'] > 0:
                nombres_salidas.append(f"{idx}: {dev['name']}")
        return nombres_salidas
    except Exception:
        return ["Predeterminado del Sistema"]

def generar_tono(frecuencia, duracion, sample_rate):
    """Genera un tono puro de una frecuencia y duración exacta."""
    t = np.linspace(0, duracion, int(sample_rate * duracion), endpoint=False)
    audio = np.sin(2 * np.pi * frecuencia * t)
    return audio

def generar_tono_alternado(f1, f2, duracion, tasa_cambio, sample_rate):
    """Genera los tonos de sincronismo/fase alternando entre dos frecuencias."""
    num_muestras = int(sample_rate * duracion)
    audio = np.zeros(num_muestras)
    muestras_por_ciclo = int(sample_rate / tasa_cambio)
    
    frecuencia_actual = f1
    fase = 0.0
    
    for i in range(num_muestras):
        if i % muestras_por_ciclo == 0:
            frecuencia_actual = f2 if frecuencia_actual == f1 else f1
        audio[i] = math.sin(fase)
        fase += 2 * math.pi * frecuencia_actual / sample_rate
        
    return audio

def reproducir_audio_generado():
    """Reproduce el WAV usando la tarjeta de sonido seleccionada por el usuario."""
    archivo_wav = "wefax_output.wav"
    
    if not os.path.exists(archivo_wav):
        messagebox.showerror("Error", "No se encontró el archivo 'wefax_output.wav'.")
        return
    
    label_estado.config(text="Reproduciendo audio por la tarjeta seleccionada...", fg="#7ed321")
    ventana.update()
    
    try:
        fs, audio_data = wav.read(archivo_wav)
        if audio_data.dtype == np.int16:
            audio_data = audio_data / 32768.0

        seleccion = combo_audio.get()
        
        if seleccion == "Predeterminado del Sistema":
            sd.play(audio_data, fs)
        else:
            id_dispositivo = int(seleccion.split(":")[0])
            sd.play(audio_data, fs, device=id_dispositivo)
            
    except Exception as e:
        messagebox.showerror("Error de Audio", f"No se pudo reproducir en esa tarjeta:\n{str(e)}")

def seleccionar_imagen():
    """Abre el explorador de archivos para elegir la foto."""
    ruta_archivo = filedialog.askopenfilename(
        title="Selecciona la imagen para el WEFAX",
        filetypes=[("Imágenes Soportadas", "*.png *.jpg *.jpeg *.tiff *.tif")]
    )
    if ruta_archivo:
        entrada_ruta.delete(0, tk.END)
        entrada_ruta.insert(0, ruta_archivo)
        label_estado.config(text="Imagen cargada correctamente", fg="#4a90e2")
        boton_reproducir.config(state=tk.DISABLED, bg="#555555")

def iniciar_codificacion():
    """Ejecuta el algoritmo de conversión de imagen a audio analógico WEFAX."""
    ruta_imagen = entrada_ruta.get()
    
    if not ruta_imagen or not os.path.exists(ruta_imagen):
        messagebox.showerror("Error", "Por favor, selecciona una imagen válida primero.")
        return
    
    label_estado.config(text="Modulando WEFAX... Por favor espera.", fg="#f5a623")
    ventana.update()
    
    try:
        img = Image.open(ruta_imagen).convert('L')
        alto_original, ancho_original = img.size[1], img.size[0]
        alto_fax = int((ANCHO_FAX / ancho_original) * alto_original)
        img = img.resize((ANCHO_FAX, alto_fax), Image.Resampling.LANCZOS)
        img_data = np.array(img)

        audio_partes = []

        # Señal de Inicio
        tono_inicio = generar_tono_alternado(F_CARRIER + F_DEV, F_CARRIER - F_DEV, 5.0, F_START, SAMPLE_RATE)
        audio_partes.append(tono_inicio)

        # Señal de Fase
        duracion_linea = 60.0 / LPM  
        muestras_linea = int(SAMPLE_RATE * duracion_linea)
        linea_fase = np.ones(muestras_linea) * (F_CARRIER + F_DEV) 
        num_muestras_negro = int(muestras_linea * 0.05)            
        linea_fase[:num_muestras_negro] = F_CARRIER - F_DEV       
        fase_total_muestras = int(SAMPLE_RATE * 20.0)
        lineas_fase_necesarias = int(fase_total_muestras / muestras_linea)
        fase_frecuencias = np.tile(linea_fase, lineas_fase_necesarias)
        fase_fases = np.cumsum(2 * np.pi * fase_frecuencias / SAMPLE_RATE)
        audio_partes.append(np.sin(fase_fases))

        # Modulación de Imagen
        muestras_pixel_por_linea = int(muestras_linea * 0.95) 
        muestras_pulso_sincro = muestras_linea - muestras_pixel_por_linea
        frecuencias_imagen = []
        
        for fila in range(alto_fax):
            frecuencias_linea = [F_CARRIER - F_DEV] * muestras_pulso_sincro
            for col in range(ANCHO_FAX):
                pixel = img_data[fila, col] / 255.0  
                frecuencia = F_CARRIER + (pixel * 2 - 1) * F_DEV
                num_repeticiones = int(muestras_pixel_por_linea / ANCHO_FAX)
                frecuencias_linea.extend([frecuencia] * num_repeticiones)
            while len(frecuencias_linea) < muestras_linea:
                frecuencias_linea.append(F_CARRIER + F_DEV)
            frecuencias_imagen.extend(frecuencias_linea[:muestras_linea])
            
        frecuencias_imagen = np.array(frecuencias_imagen)
        fases_imagen = np.cumsum(2 * np.pi * frecuencias_imagen / SAMPLE_RATE)
        audio_partes.append(np.sin(fases_imagen))

        # Tono de Parada
        tono_parada = generar_tono_alternado(F_CARRIER + F_DEV, F_CARRIER - F_DEV, 5.0, F_STOP, SAMPLE_RATE)
        audio_partes.append(tono_parada)

        # Cierre
        tono_cierre = generar_tono(F_CARRIER - F_DEV, 10.0, SAMPLE_RATE)
        audio_partes.append(tono_cierre)

        # Guardar archivo
        audio_completo = np.concatenate(audio_partes)
        audio_normalizado = np.int16(audio_completo * 32767)
        wav.write("wefax_output.wav", SAMPLE_RATE, audio_normalizado)
        
        label_estado.config(text="¡Audio generado con éxito!", fg="#7ed321")
        messagebox.showinfo("¡Éxito!", "Se ha creado 'wefax_output.wav'.")
        boton_reproducir.config(state=tk.NORMAL, bg="#ff9f43")
        
    except Exception as e:
        label_estado.config(text="Error en el proceso", fg="#d0021b")
        messagebox.showerror("Error", f"No se pudo codificar:\n{str(e)}")

# --- CONFIGURACIÓN DE LA INTERFAZ GRÁFICA (GUI) ---
ventana = tk.Tk()
ventana.title("ElGabDEV - WeFax Encoder v2")
ventana.geometry("550x340") 
ventana.resizable(False, False)
ventana.configure(bg="#1e1e1e")

label_titulo = tk.Label(
    ventana, 
    text="Codificador WEFAX v2 (120 LPM / IOC 576)", 
    font=("Arial", 14, "bold"),
    bg="#1e1e1e",
    fg="#ffffff"
)
label_titulo.pack(pady=15)

frame_archivo = tk.Frame(ventana, bg="#1e1e1e")
frame_archivo.pack(pady=5, fill=tk.X, padx=20)

entrada_ruta = tk.Entry(
    frame_archivo, 
    font=("Arial", 10),
    bg="#2d2d2d",
    fg="#ffffff",
    insertbackground="white",
    relief=tk.FLAT
)
entrada_ruta.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, ipady=4)

boton_buscar = tk.Button(
    frame_archivo, 
    text="Buscar Foto", 
    font=("Arial", 9, "bold"),
    bg="#4a90e2",
    fg="white",
    relief=tk.GROOVE,
    command=seleccionar_imagen
)
boton_buscar.pack(side=tk.RIGHT, padx=5)

frame_audio = tk.Frame(ventana, bg="#1e1e1e")
frame_audio.pack(pady=15, fill=tk.X, padx=25)

label_audio = tk.Label(
    frame_audio, 
    text="Tarjeta de Sonido (Output):", 
    font=("Arial", 10, "bold"),
    bg="#1e1e1e",
    fg="#ffffff"
)
label_audio.pack(anchor=tk.W, pady=2)

lista_dispositivos = obtener_tarjetas_audio()
combo_audio = ttk.Combobox(frame_audio, values=lista_dispositivos, state="readonly", font=("Arial", 10))
combo_audio.set("Predeterminado del Sistema")
combo_audio.pack(fill=tk.X, ipady=2)

frame_botones = tk.Frame(ventana, bg="#1e1e1e")
frame_botones.pack(pady=10)

boton_procesar = tk.Button(
    frame_botones, 
    text="1. GENERAR AUDIO .WAV", 
    font=("Arial", 10, "bold"), 
    bg="#7ed321", 
    fg="white",
    width=22,
    command=iniciar_codificacion
)
boton_procesar.pack(side=tk.LEFT, padx=10)

boton_reproducir = tk.Button(
    frame_botones, 
    text="2. REPRODUCIR AUDIO", 
    font=("Arial", 10, "bold"), 
    bg="#555555", 
    fg="white",
    width=22,
    state=tk.DISABLED,
    command=reproducir_audio_generado
)
boton_reproducir.pack(side=tk.LEFT, padx=10)

label_estado = tk.Label(
    ventana, 
    text="Estado: Esperando imagen...", 
    font=("Arial", 9, "italic"),
    bg="#1e1e1e",
    fg="#888888"
)
label_estado.pack(pady=5)

ventana.mainloop()