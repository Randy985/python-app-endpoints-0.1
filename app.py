from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rembg import remove
from PIL import Image
import io
import os
import uuid  # Para generar nombres de archivo únicos
import logging

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
CORS(app)

# Definir carpeta para guardar imágenes
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def compress_image(image_bytes, target_size_kb=200):
    input_image = Image.open(io.BytesIO(image_bytes))
    input_image = input_image.convert("RGBA")  # Asegurarse de que la imagen esté en modo RGBA
    
    # Crear una nueva imagen con fondo blanco del mismo tamaño que la imagen original
    white_bg = Image.new("RGBA", input_image.size, "white")
    # Combinar la imagen original con el fondo blanco
    merged_image = Image.alpha_composite(white_bg, input_image)
    merged_image = merged_image.convert("RGB")  # Convertir a RGB ya que JPEG no soporta transparencia

    output_io = io.BytesIO()
    quality = 90  # Calidad inicial de la compresión
    while quality > 10:  # Calidad mínima para asegurar que el bucle se detenga en algún punto
        output_io.seek(0)  # Reiniciar el buffer de IO
        output_io.truncate()  # Limpiar el buffer de IO
        merged_image.save(output_io, format='JPEG', quality=quality)  # Guardar la imagen con la calidad actual
        filesize_kb = len(output_io.getvalue()) / 1024  # Obtener el tamaño del archivo en KB
        if filesize_kb <= target_size_kb:
            break  # Si el tamaño del archivo está por debajo del objetivo, detener el proceso
        quality -= 5  # Si el tamaño del archivo está por encima del objetivo, reducir la calidad
    return output_io.getvalue()

@app.route('/compress', methods=['POST'])
def compress():
    files = request.files.getlist('images')
    compressed_image_urls = []  # Lista para almacenar las URLs de las imágenes comprimidas.
    logging.info("Pasando por el endpoint de compresión")
    for file in files:
        original_size = len(file.read())
        logging.info(f'Tamaño original: {original_size / (1024 * 1024):.2f} MB')
        file.seek(0)  # resetear el puntero del archivo para poder leerlo de nuevo
        compressed_image = compress_image(file.read())
        compressed_size = len(compressed_image)
        logging.info(f'Tamaño comprimido: {compressed_size / (1024 * 1024):.2f} MB')
        
        # Guardar la imagen comprimida en la carpeta 'uploads'
        filename = str(uuid.uuid4()) + '.jpg'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as image_file:
            image_file.write(compressed_image)
        # Agregar la URL de la imagen comprimida a la lista
        compressed_image_urls.append(request.url_root + 'uploads/' + filename)

    return jsonify({'images': compressed_image_urls})


@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    files = request.files.getlist('images')
    bg_removed_image_urls = []  # Lista para almacenar las URLs de las imágenes sin fondo.
    logging.info("Pasando por el endpoint de eliminación de fondo")
    for file in files:
        size_before = len(file.read())
        logging.info(f'Tamaño antes de eliminar el fondo: {size_before / (1024 * 1024):.2f} MB')
        file.seek(0)  # resetear el puntero del archivo para poder leerlo de nuevo
        output_image = remove(file.read())
        size_after = len(output_image)
        logging.info(f'Tamaño después de eliminar el fondo: {size_after / (1024 * 1024):.2f} MB')
        
        # Guardar la imagen sin fondo en la carpeta 'uploads'
        filename = str(uuid.uuid4()) + '.png'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as image_file:
            image_file.write(output_image)
        # Agregar la URL de la imagen sin fondo a la lista
        bg_removed_image_urls.append(request.url_root + 'uploads/' + filename)

    return jsonify({'images': bg_removed_image_urls})

if __name__ == '__main__':
    app.run(host='0.0.0.0')