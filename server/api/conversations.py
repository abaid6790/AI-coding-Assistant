"""
Conversation CRUD (from Phase 3) plus AI chat (Phase 7): posting a
message runs it through AIService with controlled context selection
(services/chat/chat_context.py) and persists both sides of the exchange.

The user's message is always saved BEFORE calling the AI provider, so a
provider failure never loses what the user typed — same expectation any
real chat app sets.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from extensions import db, limiter
from models.conversation import Conversation
from models.message import Message
from models.project import Project
from models.project_file import ProjectFile
from utils.ownership import get_owned_or_404, owned_query
from utils.validation import error_response
from services.ai.base import AIProviderError, AIProviderUnavailable
from services.ai.service import AIService
from services.chat.chat_context import build_prompt, default_title_from_message, SYSTEM_PROMPT

conversations_bp = Blueprint("conversations", __name__, url_prefix="/api/conversations")

MAX_MESSAGE_CHARS = 8000


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------
@conversations_bp.route("", methods=["GET"])
@login_required
def list_conversations():
    query = owned_query(Conversation)
    project_id = request.args.get("project_id")
    if project_id:
        query = query.filter_by(project_id=project_id)
    conversations = query.order_by(Conversation.updated_at.desc()).all()
    return jsonify({"conversations": [c.to_dict() for c in conversations]})


@conversations_bp.route("", methods=["POST"])
@login_required
def create_conversation():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "New conversation").strip()
    project_id = data.get("project_id")

    if project_id:
        get_owned_or_404(Project, project_id)

    conversation = Conversation(user_id=current_user.id, project_id=project_id, title=title)
    db.session.add(conversation)
    db.session.commit()
    return jsonify({"conversation": conversation.to_dict()}), 201


@conversations_bp.route("/<conversation_id>", methods=["GET"])
@login_required
def get_conversation(conversation_id):
    conversation = get_owned_or_404(Conversation, conversation_id)
    return jsonify({
        "conversation": conversation.to_dict(),
        "messages": [m.to_dict() for m in conversation.messages],
    })


@conversations_bp.route("/<conversation_id>", methods=["PATCH"])
@login_required
def rename_conversation(conversation_id):
    conversation = get_owned_or_404(Conversation, conversation_id)
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return error_response("Title cannot be empty.", field_errors={"title": "required"})
    conversation.title = title
    db.session.commit()
    return jsonify({"conversation": conversation.to_dict()})


@conversations_bp.route("/<conversation_id>", methods=["DELETE"])
@login_required
def delete_conversation(conversation_id):
    conversation = get_owned_or_404(Conversation, conversation_id)
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted."})


# ---------------------------------------------------------------------------
# AI chat (Phase 7)
# ---------------------------------------------------------------------------
def _resolve_context_file(conversation, file_id):
    """A file offered as chat context must belong to the same project as
    the conversation — otherwise a client could pull another project's
    file content into a conversation via this side channel."""
    if not file_id:
        return None
    file_ = get_owned_or_404(ProjectFile, file_id)
    if conversation.project_id is None or file_.project_id != conversation.project_id:
        return None
    return file_


def _run_ai_and_persist(conversation, prompt, provider_name):
    """Shared by send-message and regenerate. Returns (AIResponse, error_response_or_None)."""
    ai_service = AIService(current_app.config)
    try:
        return ai_service.generate(prompt, provider=provider_name, system=SYSTEM_PROMPT), None
    except AIProviderUnavailable as exc:
        current_app.logger.warning("AI provider unavailable: %s", exc)
        return None, error_response(
            "The AI assistant is temporarily unavailable. Your message was saved — please try again shortly.",
            status=503,
        )
    except AIProviderError as exc:
        current_app.logger.error("AI provider error: %s", exc)
        return None, error_response(
            "The AI assistant couldn't process that request. Please rephrase and try again.",
            status=502,
        )


@conversations_bp.route("/<conversation_id>/messages", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def send_message(conversation_id):
    conversation = get_owned_or_404(Conversation, conversation_id)
    data = request.get_json(silent=True) or {}

    content = (data.get("content") or "").strip()
    if not content:
        return error_response("Message cannot be empty.", field_errors={"content": "required"})
    if len(content) > MAX_MESSAGE_CHARS:
        return error_response("Message is too long.", field_errors={"content": "max_length"})

    context_file = _resolve_context_file(conversation, data.get("file_id"))
    selection = (data.get("selection") or "").strip() or None
    provider_name = data.get("provider") or conversation.provider

    # Persist the user's message first — a downstream AI failure must
    # never lose what they typed. Check "is this the first message"
    # BEFORE adding it: SQLAlchemy autoflushes on the count() query, so
    # checking after would count the just-added row and always be False.
    is_first_message = conversation.messages.count() == 0

    user_message = Message(conversation_id=conversation.id, role="user", content=content)
    db.session.add(user_message)

    if is_first_message and conversation.title == "New conversation":
        conversation.title = default_title_from_message(content)

    db.session.commit()

    prompt = build_prompt(
        conversation_messages=list(conversation.messages)[:-1],  # history excludes the message just added
        new_message=content,
        file=context_file,
        selection=selection,
    )

    ai_response, err = _run_ai_and_persist(conversation, prompt, provider_name)
    if err is not None:
        return err

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response.text,
        provider=ai_response.provider,
        model=ai_response.model,
    )
    conversation.provider = ai_response.provider
    conversation.model = ai_response.model
    db.session.add(assistant_message)
    db.session.commit()

    return jsonify({
        "conversation": conversation.to_dict(),
        "user_message": user_message.to_dict(),
        "assistant_message": assistant_message.to_dict(),
    }), 201


@conversations_bp.route("/<conversation_id>/messages/<message_id>/regenerate", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def regenerate_message(conversation_id, message_id):
    """Re-runs the AI on the same preceding context and replaces this
    assistant message's content in place, rather than appending a new
    message — that's what "regenerate" means to the person using it."""
    conversation = get_owned_or_404(Conversation, conversation_id)
    target = Message.query.filter_by(id=message_id, conversation_id=conversation.id).first()

    if target is None or target.role != "assistant":
        return error_response("That message can't be regenerated.", status=404)

    all_messages = list(conversation.messages)
    try:
        target_index = next(i for i, m in enumerate(all_messages) if m.id == target.id)
    except StopIteration:
        return error_response("That message can't be regenerated.", status=404)

    preceding = all_messages[:target_index]
    if not preceding or preceding[-1].role != "user":
        return error_response("There's no preceding user message to regenerate a reply for.", status=400)

    data = request.get_json(silent=True) or {}
    context_file = _resolve_context_file(conversation, data.get("file_id"))
    selection = (data.get("selection") or "").strip() or None
    provider_name = data.get("provider") or conversation.provider

    prompt = build_prompt(
        conversation_messages=preceding[:-1],
        new_message=preceding[-1].content,
        file=context_file,
        selection=selection,
    )

    ai_response, err = _run_ai_and_persist(conversation, prompt, provider_name)
    if err is not None:
        return err

    target.content = ai_response.text
    target.provider = ai_response.provider
    target.model = ai_response.model
    conversation.provider = ai_response.provider
    conversation.model = ai_response.model
    db.session.commit()

    return jsonify({"conversation": conversation.to_dict(), "assistant_message": target.to_dict()})
