import os
import json
from flask import Flask, request, render_template, redirect,Response
import io
from google.cloud import storage
import google.generativeai as genai
from PIL import Image

BUCKET_NAME = os.environ.get("BUCKET_NAME")

storage_client = storage.Client()

GEMINI_API = os.environ.get("GEMINI_API")

genai.configure(api_key= GEMINI_API)

ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png"}

model = genai.GenerativeModel(model_name="gemini-1.5-flash")

PROMPT = """
Generate simple title and description for this image in json format
"""
model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
#   generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    # print(file)
    return file

app = Flask(__name__)

def allowed_file(filename):
    """Check if the uploaded file is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def list_uploaded_images():
    """Fetch images from Google Cloud Storage and return metadata with signed URLs."""

    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = bucket.list_blobs()
    images = []

    for blob in blobs:
        if blob.name.endswith((".jpg", ".jpeg", ".png")):
    
            images.append(blob.name)


    return images

### **📌 Routes**

@app.route("/")
def index():
    """Render the homepage with uploaded images."""
    images = list_uploaded_images()
    return render_template("index.html", images=images)


@app.route("/upload", methods=["POST"])
def upload():
    """Upload an image, process it, and redirect to the results page."""
    
    file = request.files["form_file"]

    bucket = storage_client.bucket(BUCKET_NAME)
    blob_image = bucket.blob(file.filename)
    blob_image.upload_from_file(file_obj=file, rewind=True)
    file.save(os.path.join("",file.filename))
    response = model.generate_content(
    [Image.open(file),PROMPT]
    )

    print(response.text)
    left_index=response.text.index("{")
    right_index=response.text.index("}")
    json_string=response.text[left_index:right_index+1]
    print(json_string)
    json_string=json.loads(json_string)
    with open(file.filename.split(".")[0]+".json","w") as f:
        json.dump(json_string,f)
  
    blob_image = bucket.blob(file.filename.split(".")[0]+".json")
    blob_image.upload_from_filename(file.filename.split(".")[0]+".json")
    os.remove(file.filename.split(".")[0]+".json")
    os.remove(file.filename)

    return redirect("/")

@app.route("/files/<filename>")
def fetch_data(filename):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename.split(".")[0]+".json")
    file_data = blob.download_as_bytes()
    json_text = file_data.decode("utf-8")
    json_object = json.loads(json_text)
    html = f""" 
        <body>
        <img src="/images/{filename}" width="30%">
    <p> title:{json_object["title"]} </p>
    <p> description:{json_object["description"]} </p>
        </body>
     """
    return html

@app.route("/images/<imagename>")
def image(imagename):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(imagename)
    file_data = blob.download_as_bytes()
    return Response(io.BytesIO(file_data), mimetype='image/jpeg')



if __name__ == "__main__":
    app.run(host="localhost", port=9022)  # Listen on all interfaces
