"""
Flask Blueprint for AI editing draft endpoints — Issue #14.

Routes:
  POST /editing/drafts             — Create a new draft (201)
  GET  /editing/drafts/<draft_id>  — Fetch a draft (200/404)
  PUT  /editing/drafts/<draft_id>  — Update draft content (200)
  GET  /editor                     — Render editor page (200/400/404)
"""

from flask import Blueprint, request, jsonify, render_template, abort

import db_service

editing_bp = Blueprint("editing", __name__)


@editing_bp.route("/editing/drafts", methods=["POST"])
def create_draft():
    body = request.get_json(silent=True) or {}
    video_id = body.get("video_id")
    video_name = body.get("video_name")
    content = body.get("content")

    if not video_id or not video_name or content is None:
        return jsonify({"error": "video_id, video_name, and content are required"}), 400

    draft_id = db_service.create_draft(video_id, video_name, content)
    return jsonify({"draft_id": draft_id}), 201


@editing_bp.route("/editing/drafts/<int:draft_id>", methods=["GET"])
def get_draft(draft_id):
    draft = db_service.get_draft(draft_id)
    if draft is None:
        abort(404)
    return jsonify(draft)


@editing_bp.route("/editing/drafts/<int:draft_id>", methods=["PUT"])
def update_draft(draft_id):
    body = request.get_json(silent=True) or {}
    content = body.get("content")

    if content is None:
        return jsonify({"error": "content is required"}), 400

    transcript = body.get("transcript")
    db_service.update_draft(draft_id, content, transcript)
    return jsonify({"status": "ok"})


@editing_bp.route("/editor", methods=["GET"])
def editor():
    draft_id_str = request.args.get("draft_id")
    if not draft_id_str:
        abort(400)

    try:
        draft_id = int(draft_id_str)
    except ValueError:
        abort(400)

    draft = db_service.get_draft(draft_id)
    if draft is None:
        abort(404)

    return render_template("editor.html", draft=draft)
