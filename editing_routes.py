"""
Flask Blueprint for AI editing draft endpoints — Issue #14.

Routes:
  POST /editing/drafts             — Create a new draft (201)
  GET  /editing/drafts/<draft_id>  — Fetch a draft (200/404)
  PUT  /editing/drafts/<draft_id>  — Update draft content (200)
  GET  /editor                     — Render editor page (200/400/404)
  GET  /editing/skills             — List available skills (200)
  GET  /editing/skill/<name>       — Get full skill data (200/404)
"""

from flask import Blueprint, request, jsonify, render_template, abort, Response, stream_with_context

import db_service
import skills_service
import editing_service

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


@editing_bp.route("/editing/skills", methods=["GET"])
def list_skills():
    """Return list of available skills."""
    skills = skills_service.list_skills()
    return jsonify(skills)


@editing_bp.route("/editing/skill/<skill_name>", methods=["GET"])
def get_skill(skill_name):
    """Return the full skill data (front matter + prompt body)."""
    try:
        skill_data = skills_service.get_skill_data(skill_name)
        return jsonify(skill_data)
    except FileNotFoundError:
        abort(404)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@editing_bp.route("/editing/stream", methods=["POST"])
def stream_edit():
    """
    Stream AI-edited content via SSE.
    
    Request body:
      {
        "draft_id": int,
        "skill_name": str,
        "system_prompt_override": str (optional),
        "transcript_override": str (optional),
        "messages": list (optional, reserved for multi-turn)
      }
    
    Response: text/event-stream with JSON chunks:
      data: {"delta": "...", "done": false}
      data: {"done": true}
    """
    data = request.get_json()
    draft_id = data.get('draft_id')
    skill_name = data.get('skill_name')
    mode_name = data.get('mode_name')
    parameters = data.get('parameters') or {}
    system_prompt_override = data.get('system_prompt_override')
    transcript_override = data.get('transcript_override')

    if not draft_id or not skill_name:
        return jsonify({'error': 'draft_id and skill_name required'}), 400

    if not editing_service.is_configured():
        return jsonify({'error': 'Editing service not configured. Set EDITING_API_KEY.'}), 503

    draft = db_service.get_draft(draft_id)
    if not draft:
        abort(404)

    # Build system prompt
    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
        try:
            system_prompt = skills_service.get_skill_prompt(skill_name)
        except FileNotFoundError:
            return jsonify({'error': f'Skill not found: {skill_name}'}), 404

        if mode_name:
            try:
                skill_data = skills_service.get_skill_data(skill_name)
                mode_label = next(
                    (m.get('label', mode_name) for m in (skill_data.get('modes') or [])
                     if m.get('name') == mode_name),
                    mode_name
                )
                system_prompt = f"Mode: {mode_label}\n\n{system_prompt}"
            except (FileNotFoundError, ValueError):
                pass

        # Validate required parameters
        try:
            merged_params = skills_service.get_merged_parameters(skill_name, mode_name)
        except (FileNotFoundError, ValueError):
            merged_params = []

        for param in merged_params:
            if param.get('required') and not str(parameters.get(param['name'], '')).strip():
                return jsonify({'error': f"Required parameter missing: {param['label']}"}), 400

    transcript = transcript_override or draft.get('transcript')

    def generate():
        yield from editing_service.stream_edit(system_prompt, draft['content'], transcript, parameters=parameters or None)

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@editing_bp.route('/editing/drafts/<int:draft_id>/versions', methods=['GET'])
def list_versions(draft_id):
    """Return list of saved draft versions ordered by created_at descending."""
    draft = db_service.get_draft(draft_id)
    if not draft:
        abort(404)
    versions = db_service.list_draft_versions(draft_id)
    return jsonify(versions)


@editing_bp.route('/editing/drafts/<int:draft_id>/restore/<int:version_id>', methods=['POST'])
def restore_version(draft_id, version_id):
    """Restore draft to a specific version and create new version entry."""
    draft = db_service.get_draft(draft_id)
    if not draft:
        abort(404)
    try:
        db_service.restore_draft_version(draft_id, version_id)
    except ValueError:
        abort(404)
    return jsonify(db_service.get_draft(draft_id))
