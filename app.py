from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rembg import remove
from PIL import Image
import io
import os
import uuid

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def compress_image(image_bytes, target_size_kb=200):
    input_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    
    white_bg = Image.new("RGBA", input_image.size, "white")
    merged_image = Image.alpha_composite(white_bg, input_image).convert("RGB")

    output_io = io.BytesIO()
    quality = 90
    while quality > 10:
        output_io.seek(0)
        output_io.truncate()
        merged_image.save(output_io, format='JPEG', quality=quality)
        if len(output_io.getvalue()) / 1024 <= target_size_kb:
            break
        quality -= 5
    return output_io.getvalue()

@app.route('/compress', methods=['POST'])
def compress():
    compressed_image_urls = []
    for file in request.files.getlist('images'):
        compressed_image = compress_image(file.read())
        filename = str(uuid.uuid4()) + '.jpg'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as image_file:
            image_file.write(compressed_image)
        compressed_image_urls.append(request.url_root + 'uploads/' + filename)
    return jsonify({'images': compressed_image_urls})

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    bg_removed_image_urls = []
    for file in request.files.getlist('images'):
        output_image = remove(file.read())
        filename = str(uuid.uuid4()) + '.png'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as image_file:
            image_file.write(output_image)
        bg_removed_image_urls.append(request.url_root + 'uploads/' + filename)
    return jsonify({'images': bg_removed_image_urls})

if __name__ == '__main__':
    print("Ejecutando la aplicación...")
    port = int(os.environ.get("FLASK_APP_PORT", 5000))
    app.run(host='0.0.0.0', port=port)
