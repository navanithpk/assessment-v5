from flask import Flask, render_template, request, jsonify
import os, base64

app = Flask(__name__)

OUTPUT = "output"
os.makedirs(OUTPUT, exist_ok=True)


@app.route("/")
def home():
    processed = {
        f.split("_slice_")[0]
        for f in os.listdir(OUTPUT)
        if f.endswith(".png")
    }
    return render_template("index.html", processed=list(processed))


@app.route("/save_slices", methods=["POST"])
def save_slices():

    data = request.json
    filename = data["filename"]
    images = data["images"]

    for i, img in enumerate(images, 1):
        b64 = img.split(",")[1]
        with open(f"{OUTPUT}/{filename}_slice_{i}.png", "wb") as f:
            f.write(base64.b64decode(b64))

    return jsonify(success=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

