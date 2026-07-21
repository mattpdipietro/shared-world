"""Entitlement policy seam.

See docs/data-model.md#authentication-and-entitlements — editing rights are
entitlement-based *in design*, fully open *in practice* for now. Every write
path should route through `has_permission` rather than checking roles
directly, so tightening access later is a change to this one function (and
whatever entitlement data eventually backs it) instead of a hunt through
every route.
"""

from __future__ import annotations

from app.db.models import Person


def has_permission(person: Person, action: str, resource: str) -> bool:
    """Check whether a person may perform an action on a resource.

    Args:
        person: The person attempting the action.
        action: A short verb describing the attempt, e.g. `"edit"`, `"delete"`.
        resource: What's being acted on, e.g. `"session:1234"`, `"note:5678"`.

    Returns:
        Always `True` for now — no permissions table exists yet because
        every logged-in person currently has full access.
    """
    return True
