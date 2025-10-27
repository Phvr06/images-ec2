import os
import io
import base64
import boto3
from decimal import Decimal
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS

# Config via ENV
AWS_REGION   = os.environ.get("AWS_REGION", "us-east-2")
S3_BUCKET    = os.environ.get("S3_BUCKET", "objects-clouda")
DDB_TABLE    = os.environ.get("DDB_TABLE", "images-base64")
PRESIGN_EXP  = int(os.environ.get("PRESIGN_EXP", "300"))  # segundos

# Clients
s3_client = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DDB_TABLE)

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/upload-url", methods=["POST"])
def upload_url():
    """
    Recebe JSON:
    {
      "filename": "path/para/arquivo.jpg",
      "contentType": "image/png"
    }
    Retorna:
    {
      "uploadUrl": "...",
      "key": "path/para/arquivo.jpg",
      "expiresIn": 300
    }
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
    Recupera todos os chunks para imageId da tabela DynamoDB,
    ordena por chunkId e retorna a imagem binária.
    """
    # Query DynamoDB por partition key imageId
    try:
        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("imageId").eq(image_id)
        )
    except Exception as e:
        app.logger.exception("Erro consultando DynamoDB")
        return jsonify({"error": "dynamodb query failed", "detail": str(e)}), 500

    items = resp.get("Items", [])
    if not items:
        return abort(404, description="Image not found")

    # Ordena por chunkId (pode vir como Decimal)
    try:
        items_sorted = sorted(items, key=lambda x: int(x.get("chunkId", 0)))
    except Exception:
        items_sorted = items

    # Concatena as strings base64 e decodifica
    try:
        b64_parts = [it["data"] for it in items_sorted]
        b64_full = "".join(b64_parts)
        image_bytes = base64.b64decode(b64_full)
    except Exception as e:
        app.logger.exception("Erro reconstituindo imagem")
        return jsonify({"error": "failed to rebuild image", "detail": str(e)}), 500

    # Tenta recuperar contentType do primeiro item se existir
    content_type = items_sorted[0].get("contentType", "application/octet-stream")

    # Retorna como arquivo binário
    return send_file(
        io.BytesIO(image_bytes),
        mimetype=content_type,
        as_attachment=False,
        download_name=image_id
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host="0.0.0.0", port=port)
