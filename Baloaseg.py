import cv2
import argparse
import numpy as np
import os
from tqdm import tqdm  # Importar tqdm para la barra de progreso
import time  # Para medir el tiempo de exportación

# Configuración de parámetros
initial_canvas_width = 1920  # Ancho inicial del lienzo de salida
initial_canvas_height = 1080  # Alto inicial del lienzo de salida
move_step = 350  # Número de píxeles que la cámara se moverá con cada pulsación de tecla
zoom_step = 0.1  # Paso de zoom
anticipation_frames = 30  # Número de frames de anticipación para suavizar el movimiento
playback_speed = 4  # Velocidad de reproducción durante la edición (4x velocidad)

# Variables globales para el control del teclado
canvas_start_x, canvas_start_y = 0, 0
canvas_width, canvas_height = initial_canvas_width, initial_canvas_height

# Marcador
local_score = 0
visitor_score = 0
goal_events = []  # Lista para registrar los eventos de gol

# Almacenar posiciones de la cámara para suavizar el movimiento
camera_positions = []
key_frames = []

# Variable para controlar si está grabando después de presionar 'p'
recording = False
start_time_export = None  # Para guardar el tiempo de inicio de la exportación

def draw_scoreboard(frame, local_score, visitor_score):
    scoreboard_text = f"Local {local_score} - {visitor_score} Visitante"
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, scoreboard_text, (10, 30), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

def draw_progress_bar(frame, current_frame, total_frames):
    # Tamaño de la barra
    bar_width = frame.shape[1] - 40  # Ancho de la barra (ancho del frame menos margen)
    bar_height = 20  # Alto de la barra
    x_start = 20  # Margen izquierdo
    y_start = frame.shape[0] - 50  # Posición vertical desde la parte inferior

    # Fondo negro detrás de la barra para que sea visible
    cv2.rectangle(frame, (x_start, y_start), (x_start + bar_width, y_start + bar_height), (0, 0, 0), -1)

    # Progreso
    progress = int((current_frame / total_frames) * bar_width)

    # Dibujar el progreso (verde)
    cv2.rectangle(frame, (x_start, y_start), (x_start + progress, y_start + bar_height), (0, 255, 0), -1)

    # Mostrar el tiempo actual y el tiempo total en minutos y segundos
    current_time = (current_frame / fps)  # Tiempo en segundos
    total_time = (total_frames / fps)  # Tiempo total en segundos
    time_text = f"{int(current_time // 60)}:{int(current_time % 60):02d} / {int(total_time // 60)}:{int(total_time % 60):02d}"
    
    # Dibujar el texto del tiempo sobre la barra
    cv2.putText(frame, time_text, (x_start + 5, y_start + bar_height - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

def main(video_path, temp_output_path, final_output_path):
    global canvas_start_x, canvas_start_y, canvas_width, canvas_height, camera_positions, key_frames, local_score, visitor_score, goal_events, recording, fps

    # Abrir el video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error al abrir el video")
        return

    # Obtener propiedades del video
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Crear el objeto para escribir el video de salida temporal
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Cambiado a 'mp4v' para formato MP4
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (initial_canvas_width, initial_canvas_height))

    # Configurar la ventana
    cv2.namedWindow('Control Manual del Seguimiento del Balón')

    # Variable de estado para pausar y reproducir el video
    paused = True

    frame_count = 0
    ret, frame = cap.read()  # Leer el primer frame fuera del bucle
    if not ret:
        print("Error al leer el video.")
        return

    # Recortar el primer frame y ajustarlo
    cropped_frame = frame[canvas_start_y:canvas_start_y + canvas_height, canvas_start_x:canvas_start_x + canvas_width]
    resized_frame = cv2.resize(cropped_frame, (initial_canvas_width, initial_canvas_height))

    while True:
        key = cv2.waitKey(30) & 0xFF  # Capturar la tecla presionada en cada iteración

        if not paused:  # Solo avanzar en el video si no está en pausa
            for _ in range(playback_speed - 1):  # Saltar 3 frames para alcanzar la velocidad 4x
                cap.grab()  # Leer el siguiente frame sin procesarlo

            ret, frame = cap.read()  # Leer el frame para mostrar
            if not ret:
                print("Fin del video o error en la lectura del frame.")
                break

        # Control de cámara y zoom (siempre disponible)
        if key == ord('w'):  # Mover arriba
            canvas_start_y = max(0, canvas_start_y - move_step)
        elif key == ord('s'):  # Mover abajo
            canvas_start_y = min(frame_height - canvas_height, canvas_start_y + move_step)
        elif key == ord('a'):  # Mover izquierda
            canvas_start_x = max(0, canvas_start_x - move_step)
        elif key == ord('d'):  # Mover derecha
            canvas_start_x = min(frame_width - canvas_width, canvas_start_x + move_step)
        elif key == ord('+'):  # Zoom in
            canvas_width = int(canvas_width * (1 - zoom_step))
            canvas_height = int(canvas_height * (1 - zoom_step))
            canvas_width = max(initial_canvas_width, min(frame_width, canvas_width))
            canvas_height = max(initial_canvas_height, min(frame_height, canvas_height))
            canvas_start_x = max(0, min(frame_width - canvas_width, canvas_start_x))
            canvas_start_y = max(0, min(frame_height - canvas_height, canvas_start_y))
        elif key == ord('-'):  # Zoom out
            canvas_width = int(canvas_width * (1 + zoom_step))
            canvas_height = int(canvas_height * (1 + zoom_step))
            canvas_width = max(initial_canvas_width, min(frame_width, canvas_width))
            canvas_height = max(initial_canvas_height, min(frame_height, canvas_height))
            canvas_start_x = max(0, min(frame_width - canvas_width, canvas_start_x))
            canvas_start_y = max(0, min(frame_height - canvas_height, canvas_start_y))

        # Recortar el frame según la posición del lienzo y ajustarlo
        cropped_frame = frame[canvas_start_y:canvas_start_y + canvas_height, canvas_start_x:canvas_start_x + canvas_width]
        resized_frame = cv2.resize(cropped_frame, (initial_canvas_width, initial_canvas_height))

        # Dibujar marcador
        draw_scoreboard(resized_frame, local_score, visitor_score)

        # Dibujar la barra de progreso
        draw_progress_bar(resized_frame, frame_count, total_frames)

        # Mostrar el último frame leído (ya sea pausado o no)
        cv2.imshow('Control Manual del Seguimiento del Balón', resized_frame)

        # Manejo de las teclas
        if key == ord('q'):  # Terminar el script con 'q'
            break
        elif key == ord('p'):  # Reproducir o pausar el video con 'p'
            paused = not paused  # Cambiar el estado de pausa
            if not paused:
                recording = True  # Comenzar a grabar cuando se presiona 'p'
                global start_time_export
                start_time_export = time.time()  # Comenzar a medir el tiempo desde que se presiona 'p'

        # Almacenar la posición de la cámara solo si estamos grabando
        if recording:
            camera_positions.append((canvas_start_x, canvas_start_y, canvas_width, canvas_height))
            if frame_count % anticipation_frames == 0:
                key_frames.append((canvas_start_x, canvas_start_y, canvas_width, canvas_height, frame_count))

        frame_count += 1

    # Interpolar las posiciones de la cámara para suavizar el movimiento
    interpolated_positions = []
    num_frames = len(camera_positions)

    # Comprobar si hay suficientes keyframes
    if len(key_frames) > 1:
        for i in range(1, len(key_frames)):
            start_x, start_y, start_width, start_height, start_frame = key_frames[i-1]
            end_x, end_y, end_width, end_height, end_frame = key_frames[i]

            for j in range(start_frame, end_frame):
                t = (j - start_frame) / (end_frame - start_frame)
                x = start_x + t * (end_x - start_x)
                y = start_y + t * (end_y - start_y)
                width = start_width + t * (end_width - start_width)
                height = start_height + t * (end_height - start_height)
                interpolated_positions.append((x, y, width, height))

        # Añadir la última posición
        interpolated_positions.append((end_x, end_y, end_width, end_height))
    else:
        # Si no hay suficientes keyframes, usar la última posición conocida
        interpolated_positions = [(canvas_start_x, canvas_start_y, canvas_width, canvas_height)] * num_frames

    # Exportar el video con el movimiento suavizado a velocidad normal
    export_smooth_video(video_path, final_output_path, interpolated_positions, fps)


def export_smooth_video(video_path, final_output_path, interpolated_positions, fps):
    """
    Función para exportar el video con las posiciones suavizadas de la cámara.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error al abrir el video")
        return

    # Crear el objeto para escribir el video de salida final a velocidad normal
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Cambiado a 'mp4v' para formato MP4
    out = cv2.VideoWriter(final_output_path, fourcc, fps, (initial_canvas_width, initial_canvas_height))

    frame_count = 0
    total_frames = len(interpolated_positions)

    # Mostrar duración total estimada
    video_duration = total_frames / fps  # Duración en segundos
    print(f"Duración total estimada del video: {int(video_duration // 60)}:{int(video_duration % 60):02d} minutos")

    # Barra de progreso para la exportación
    with tqdm(total=total_frames, desc="Exportando video suavizado a velocidad normal") as pbar:
        for frame_count in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break

            # Obtener las posiciones suavizadas de la cámara
            canvas_start_x, canvas_start_y, canvas_width, canvas_height = map(int, interpolated_positions[frame_count])

            # Recortar el frame según la posición suavizada del lienzo
            cropped_frame = frame[int(canvas_start_y):int(canvas_start_y) + canvas_height, int(canvas_start_x):int(canvas_start_x) + canvas_width]
            resized_frame = cv2.resize(cropped_frame, (initial_canvas_width, initial_canvas_height))

            # Dibujar marcador
            draw_scoreboard(resized_frame, local_score, visitor_score)

            out.write(resized_frame)
            pbar.update(1)

    cap.release()
    out.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control manual del movimiento de la cámara en un video de fútbol.")
    parser.add_argument("-v", "--video_path", required=True, help="Ruta del video de entrada")
    parser.add_argument("-o", "--output_path", required=True, help="Ruta del video de salida")
    
    args = parser.parse_args()
    
    temp_output_path = "temp_output.avi"
    final_output_path = args.output_path
    
    main(args.video_path, temp_output_path, final_output_path)
