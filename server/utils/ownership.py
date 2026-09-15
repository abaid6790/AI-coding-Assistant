"""
Every resource a user can own (projects, files, conversations, reviews,
generated tests, documents) must be fetched through here, never through a
raw `Model.query.get(id)`. That's the whole isolation contract in one place:

  - The owning user id ALWAYS comes from `current_user`, never from the
    request body, query string, or URL. A client can send any id it wants;
    it is never trusted as "who is asking".
  - A resource that exists but belongs to someone else returns the exact
    same 404 as a resource that doesn't exist at all. We deliberately do
    NOT distinguish "not found" from "not yours" — a 403 would leak that
    the id is valid and just belongs to another account.
"""
from flask import abort
from flask_login import current_user


def get_owned_or_404(model, resource_id, user_field: str = "user_id"):
    """Fetch a row by primary key, scoped to the current user.

    Aborts 404 (not 403) if the row doesn't exist OR belongs to someone
    else — the two cases must be indistinguishable from the outside.
    """
    if resource_id is None:
        abort(404)

    resource = model.query.filter(
        model.id == resource_id,
        getattr(model, user_field) == current_user.id,
    ).first()

    if resource is None:
        abort(404)

    return resource


def owned_query(model, user_field: str = "user_id"):
    """A base query already scoped to the current user — use this for any
    list endpoint instead of `model.query`, so listing can never leak
    another user's rows."""
    return model.query.filter(getattr(model, user_field) == current_user.id)
