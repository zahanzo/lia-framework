"""
skills.py — Chat Mode with Rotating Skills

Manages the "Chat Mode": randomly selects a skill per turn with a turn-based
cooldown to diversify responses. Skills are configured in the dashboard (Persona tab).

Chat mode can be activated by:
  - Saying phrases like "let's chat", "chat mode", "casual mode"
  - Clicking the "💬 Chat" button in the dashboard header
  - POST /api/batepapo/toggle endpoint
"""

import random
import core.config as config
from core.i18n import t

# ==========================================
# CHAT MODE STATE
# ==========================================
CHAT_MODE_ACTIVE = False

# Cooldown in turns: after using a skill it is unavailable for N turns
COOLDOWN_TURNS = 3

_current_turn    = 0
_cooldowns: dict[str, int] = {}  # {skill_id: turn_when_available_again}
_last_skill: str | None = None


# ==========================================
# ACTIVATE / DEACTIVATE
# ==========================================
def activate():
    global CHAT_MODE_ACTIVE, _current_turn, _cooldowns, _last_skill
    CHAT_MODE_ACTIVE = True
    _current_turn    = 0
    _cooldowns       = {}
    _last_skill      = None
    config.run_sql(
        "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
        ("chat_mode", "1")
    )
    print(t("skills.activated"))


def deactivate():
    global CHAT_MODE_ACTIVE
    CHAT_MODE_ACTIVE = False
    config.run_sql(
        "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
        ("chat_mode", "0")
    )
    print(t("skills.deactivated"))


def sync_state():
    """Read state from DB on startup (persists between restarts)."""
    global CHAT_MODE_ACTIVE
    res = config.run_sql(
        "SELECT text_value FROM system_state WHERE key = 'chat_mode'",
        fetch=True
    )
    CHAT_MODE_ACTIVE = bool(res and res[0][0] == "1")


def toggle() -> bool:
    """Toggle chat mode and return the new state."""
    if CHAT_MODE_ACTIVE:
        deactivate()
    else:
        activate()
    return CHAT_MODE_ACTIVE


# ==========================================
# SKILL SELECTION
# ==========================================
def _get_skills() -> list[dict]:
    """Read skills saved in the persona settings."""
    persona = config.get_setting("persona")
    return persona.get("skills", [])


def roll_skill() -> dict | None:
    """
    Pick a random skill not on cooldown.
    Returns None if chat mode is off or no skills are configured.
    """
    global _current_turn, _last_skill

    if not CHAT_MODE_ACTIVE:
        return None

    skills = _get_skills()
    if not skills:
        return None

    # Advance turn counter and expire cooldowns
    _current_turn += 1
    expired = [sid for sid, until in _cooldowns.items() if _current_turn >= until]
    for sid in expired:
        del _cooldowns[sid]

    # Available: not on cooldown AND not the last used
    available = [s for s in skills if s["id"] not in _cooldowns and s["id"] != _last_skill]

    # If all are on cooldown, relax the cooldown restriction (but not last-used)
    if not available:
        available = [s for s in skills if s["id"] != _last_skill]

    # If still empty (only 1 skill), use it anyway
    if not available:
        available = skills

    skill = random.choice(available)
    _cooldowns[skill["id"]] = _current_turn + COOLDOWN_TURNS
    _last_skill = skill["id"]

    print(t("skills.rolled", id=skill["id"], cooldowns=list(_cooldowns.keys())))
    return skill


# ==========================================
# PROMPT INJECTION
# ==========================================
def build_skill_instruction(skill: dict) -> str:
    """Format a skill instruction for injection into the AI context."""
    return (
        f"\n\n[🎭 CHAT MODE — STYLE INSTRUCTION]\n"
        f"In this response, in addition to answering normally, apply this style:\n"
        f"→ {skill['texto']}\n"
        f"Incorporate this naturally without mentioning that you are following an instruction."
    )


def get_prompt_injection() -> str:
    """Roll a skill and return the formatted instruction. Empty string if mode is off."""
    skill = roll_skill()
    return build_skill_instruction(skill) if skill else ""


# ==========================================
# STATUS (for dashboard)
# ==========================================
def get_status() -> dict:
    skills = _get_skills()
    on_cooldown = list(_cooldowns.keys())
    available   = [s["id"] for s in skills if s["id"] not in on_cooldown]
    return {
        "active":       CHAT_MODE_ACTIVE,
        "current_turn": _current_turn,
        "last_skill":   _last_skill,
        "on_cooldown":  on_cooldown,
        "available":    available,
        "total_skills": len(skills)
    }