from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rembg import remove
from PIL import Image
import io
import logging
import base64

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
CORS(app)

def image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def base64_to_image(base64_string, output_path):
    image_bytes = base64.b64decode(base64_string)
    with open(output_path, 'wb') as img_file:
        img_file.write(image_bytes)

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
    compressed_images_base64 = []  # Lista para almacenar las imágenes comprimidas en Base64.
    
    logging.info("Pasando por el endpoint de compresión")
    
    for file in files:
        original_size = len(file.read())
        logging.info(f'Tamaño original: {original_size / (1024 * 1024):.2f} MB')
        
        file.seek(0)  # resetear el puntero del archivo para poder leerlo de nuevo
        compressed_image = compress_image(file.read())
        
        # Convertir la imagen comprimida a Base64 y agregar a la lista
        compressed_images_base64.append(image_to_base64(compressed_image))

    return jsonify({'images': compressed_images_base64})

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    files = request.files.getlist('images')
    bg_removed_images_base64 = []  # Lista para almacenar las imágenes sin fondo en Base64.
    
    logging.info("Pasando por el endpoint de eliminación de fondo")
    
    for file in files:
        size_before = len(file.read())
        logging.info(f'Tamaño antes de eliminar el fondo: {size_before / (1024 * 1024):.2f} MB')
        
        file.seek(0)  # resetear el puntero del archivo para poder leerlo de nuevo
        output_image = remove(file.read())
        
        # Convertir la imagen sin fondo a Base64 y agregar a la lista
        bg_removed_images_base64.append(image_to_base64(output_image))

    return jsonify({'images': bg_removed_images_base64})

if __name__ == '__main__':
    app.run(host='0.0.0.0')