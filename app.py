from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from rembg import remove
from PIL import Image
import io
import uuid
import os

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

def generate_short_url():
    unique_id = str(uuid.uuid4()).replace('-', '')
    return f"/i/{unique_id}"

def upload_image_to_server(image_bytes):
    short_url = generate_short_url()
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], short_url.split('/')[-1] + '.png')
    print(f"Image saved at: {image_path}")
    with open(image_path, "wb") as image_file:
        image_file.write(image_bytes)
    return short_url

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    try:
        files = request.files.getlist('main_image') + request.files.getlist('additional_images')
        bg_removed_image_links = []

        for file in files:
            if file and allowed_file(file.filename):
                output_image_bytes = remove(file.stream.read())
                bg_removed_image_link = upload_image_to_server(output_image_bytes)
                bg_removed_image_links.append(bg_removed_image_link)

        return jsonify({'images': bg_removed_image_links})
    
    except Exception as e:
        print(e)
        return jsonify({'error': f'Internal Server Error: {str(e)}'}), 500


@app.route('/i/<short_id>', methods=['GET'])
def serve_image(short_id):
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], short_id + '.png')
    print(f"Trying to access image at path: {image_path}")
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/png')
    else:
        return "Image not found", 404

@app.route('/compress', methods=['POST'])
def compress():
    try:
        files = request.files.getlist('images')
        compressed_image_links = []

        for file in files:
            if file and allowed_file(file.filename):
                test_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_image_before_compression.png')
                file.save(test_image_path)  # Guarda la imagen directamente para verificarla

                file.stream.seek(0)  # Añade esta línea para reiniciar el puntero del archivo
                buffered = io.BytesIO(file.stream.read())
                input_image = Image.open(buffered)
                compressed_image_path = compress_image(input_image)
                compressed_image_link = upload_image_to_server(open(compressed_image_path, 'rb').read())
                os.remove(compressed_image_path)
                compressed_image_links.append(compressed_image_link)

        return jsonify({'images': compressed_image_links})
    
    except Exception as e:
        print(e)
        return jsonify({'error': f'Internal Server Error: {str(e)}'}), 500

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
