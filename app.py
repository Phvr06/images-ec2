import os
import io
import base64
import boto3
from flask import Flask, request, jsonify, send_file, abort, render_template
from flask_cors import CORS
from boto3.dynamodb.conditions import Key

# --------- Configurações e clientes AWS (não alterados) --------- #

AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")
S3_BUCKET = os.environ.get("S3_BUCKET", "objects-clouda")
DDB_TABLE = os.environ.get("DDB_TABLE", "images-base64")
PRESIGN_EXP = int(os.environ.get("PRESIGN_EXP", "300"))

s3_client = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DDB_TABLE)

app = Flask(__name__)
CORS(app)

# -------------------------- Rotas Flask ------------------------- #

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/upload-url", methods=["POST"])
def upload_url():
    """
    Gera uma URL pré-assinada para upload direto ao S3.
    """
    body = request.get_json(force=True, silent=True) or {}
    filename = body.get("filename")
    content_type = body.get("contentType", "application/octet-stream")

    if not filename:
        return jsonify({"error": "filename is required"}), 400

    key = filename

    try:
        presigned = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=PRESIGN_EXP,
            HttpMethod="PUT"
        )
    except Exception as e:
        app.logger.exception("Erro gerando presigned URL")
        return jsonify({"error": "failed to generate presigned url", "detail": str(e)}), 500

    return jsonify({
        "uploadUrl": presigned,
        "key": key,
        "expiresIn": PRESIGN_EXP
    })


@app.route("/api/images/<string:image_id>", methods=["GET"])
def get_image(image_id):
    """
    Recupera e retorna a imagem armazenada como binário.
    """
    try:
        resp = table.query(KeyConditionExpression=Key("imageId").eq(image_id))
        items = resp.get("Items", [])

        if not items:
            return abort(404, description="Image not found")

        items_sorted = sorted(items, key=lambda x: int(x.get("chunkId", 0)))
        b64_full = "".join(item["data"] for item in items_sorted)
        image_bytes = base64.b64decode(b64_full)

        content_type = items_sorted[0].get("contentType", "application/octet-stream")

        return send_file(
            io.BytesIO(image_bytes),
            mimetype=content_type,
            as_attachment=False,
            download_name=image_id
        )

    except Exception as e:
        app.logger.exception("Erro reconstituindo imagem")
        return jsonify({"error": "failed to rebuild image", "detail": str(e)}), 500


@app.route("/api/list-images", methods=["GET"])
def list_images():
    """
    Retorna lista de imagens com imageId e contentType.
    """
    try:
        resp = table.scan(ProjectionExpression="imageId, contentType")
        images = resp.get("Items", [])
        return jsonify(images)

    except Exception as e:
        app.logger.exception("Erro listando imagens")
        return jsonify({"error": "failed to list images", "detail": str(e)}), 500


@app.route("/api/view-image/<string:image_id>", methods=["GET"])
def view_image_base64(image_id):
    """
    Retorna a imagem como JSON contendo Base64 para consumo fácil no frontend.
    """
    try:
        resp = table.query(KeyConditionExpression=Key("imageId").eq(image_id))
        items = resp.get("Items", [])

        if not items:
            return abort(404, description="Image not found")

        items_sorted = sorted(items, key=lambda x: int(x.get("chunkId", 0)))
        b64_full = "".join(item["data"] for item in items_sorted)

        content_type = items_sorted[0].get("contentType", "application/octet-stream")

        return jsonify({
            "image_id": image_id,
            "content_type": content_type,
            "base64_data": b64_full
        })

    except Exception as e:
        app.logger.exception("Erro recuperando imagem Base64")
        return jsonify({"error": "failed to get image", "detail": str(e)}), 500


# ---------------------------- Execução ---------------------------- #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host="0.0.0.0", port=port)
