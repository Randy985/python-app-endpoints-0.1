from flask import Flask, request, jsonify
from flask_cors import CORS
from rembg import remove
from PIL import Image
import io
import pyimgur
import os

IMGUR_CLIENT_ID = '67b749b9b6bb35b'
IMGUR_CLIENT_SECRET = 'c4543eba84a80c2d9f8f2ac4af2da1caf06a2d31'
imgur = pyimgur.Imgur(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_imgur(image_bytes):
    """Sube la imagen a Imgur y devuelve la URL corta de la imagen."""
    temp_file_path = "temp_image.png"
    with open(temp_file_path, "wb") as temp_file:
        temp_file.write(image_bytes)
    uploaded_image = imgur.upload_image(temp_file_path, title="Uploaded with pyimgur")
    os.remove(temp_file_path)
    return uploaded_image.link  # la biblioteca ya devuelve una URL corta.

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    if 'main_image' not in request.files:
        return jsonify({'error': 'No main image provided'})

    main_image = request.files['main_image']
    additional_images = sorted([file for key, file in request.files.items() if 'additional_image_' in key], key=lambda x: x.filename)

    all_images = [main_image] + additional_images

    bg_removed_image_links = []

    print("Pasando por el endpoint de eliminación de fondo")

    for file in all_images:
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        if file and allowed_file(file.filename):
            output_image_bytes = remove(file.stream.read())
            bg_removed_image_link = upload_to_imgur(output_image_bytes)
            bg_removed_image_links.append(bg_removed_image_link)

    return jsonify({'images': bg_removed_image_links})


@app.route('/compress', methods=['POST'])
def compress():
    if 'images' not in request.files:
        return jsonify({'error': 'No file part'})

    files = request.files.getlist('images')
    compressed_image_links = []

    print("Pasando por el endpoint de compresión")

    for file in files:
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        if file and allowed_file(file.filename):
            file_bytes = file.stream.read()
            buffered = io.BytesIO(file_bytes)
            input_image = Image.open(buffered)
            compressed_image_path = compress_image(input_image)
            compressed_image_link = upload_to_imgur(open(compressed_image_path, 'rb').read())
            os.remove(compressed_image_path)  # Eliminar imagen temporal después de subirla.
            compressed_image_links.append(compressed_image_link)

    return jsonify({'images': compressed_image_links})

def compress_image(input_image, target_size_kb=200):
    input_image = input_image.convert("RGBA")
    white_bg = Image.new("RGBA", input_image.size, "white")
    merged_image = Image.alpha_composite(white_bg, input_image)
    merged_image = merged_image.convert("RGB")

    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'compressed.jpg')
    quality = 90
    while quality > 10:
        merged_image.save(output_path, format='JPEG', quality=quality)
        filesize_kb = os.path.getsize(output_path) / 1024
        if filesize_kb <= target_size_kb:
            break
        quality -= 5

    return output_path

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run()
