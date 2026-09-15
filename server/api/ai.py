"""
Read-only status endpoint for the frontend to know which AI providers
exist and which are actually usable. No prompt goes through here — that
starts in Phase 7 (chat) and Phase 8 (code-intelligence features), both
of which will call services.ai.service.AIService.generate() rather
than talking to a provider directly.
"""
from flask import Blueprint, current_app, jsonify
from flask_login import login_required

from services.ai.service import AIService

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.route("/providers", methods=["GET"])
@login_required
def list_providers():
    service = AIService(current_app.config)
    return jsonify({"providers": service.list_providers()})
