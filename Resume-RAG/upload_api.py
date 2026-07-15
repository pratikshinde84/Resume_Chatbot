import os
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from ingest import ingest_resumes
from rag import query_rag

app = Flask(__name__) 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "resumes")
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_unique_filename(directory: str, filename: str) -> str:
    candidate = secure_filename(filename)
    if not os.path.exists(os.path.join(directory, candidate)):
        return candidate

    base, extension = os.path.splitext(candidate)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{base}_{timestamp}{extension}"


def list_resume_files() -> list:
    return sorted([f for f in os.listdir(app.config["UPLOAD_FOLDER"]) if allowed_file(f)])


@app.route("/upload", methods=["POST"])
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "Missing file field. Use form field name 'file'."}), 400

    upload_file = request.files["file"]
    if upload_file.filename == "":
        return jsonify({"error": "No filename provided."}), 400

    if not allowed_file(upload_file.filename):
        return jsonify({"error": "Invalid file type. Only PDF files are allowed."}), 400

    saved_filename = get_unique_filename(app.config["UPLOAD_FOLDER"], upload_file.filename)
    saved_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_filename)
    upload_file.save(saved_path)

    return jsonify({
        "status": "success",
        "filename": saved_filename,
        "message": "Resume uploaded successfully to the resumes folder."
    }), 201


@app.route("/resumes", methods=["GET"])
@app.route("/resumes/", methods=["GET"])
def get_resumes():
    resumes = list_resume_files()
    return jsonify({"resumes": resumes}), 200


@app.route("/resumes/<path:filename>", methods=["DELETE"])
def delete_resume(filename: str):
    secure_name = secure_filename(filename)
    if secure_name != filename:
        return jsonify({"error": "Invalid filename."}), 400

    resume_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_name)
    if not os.path.exists(resume_path):
        return jsonify({"error": "Resume not found."}), 404

    os.remove(resume_path)
    return jsonify({"status": "success", "filename": secure_name, "message": "Resume deleted."}), 200


@app.route("/query", methods=["POST"])
def query_resume():
    payload = request.get_json(silent=True)
    if not payload or "query" not in payload:
        return jsonify({"error": "JSON body must include a 'query' field."}), 400

    query_text = payload["query"].strip()
    if not query_text:
        return jsonify({"error": "Query text cannot be empty."}), 400

    try:
        answer, sources = query_rag(query_text)
        return jsonify({"answer": answer, "sources": sources}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/rebuild", methods=["GET", "POST"])
@app.route("/rebuild/", methods=["GET", "POST"])
def rebuild_index():
    try:
        ingest_resumes()
        return jsonify({"status": "success", "message": "Resume vector database rebuilt."}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
