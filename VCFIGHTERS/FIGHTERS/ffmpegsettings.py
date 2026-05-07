# ╔══════════════════════════════════════════════════════════════╗
# ║         VCFIGHTER — FFmpeg Weapon Controls                   ║
# ║         File: VCFIGHTERS/FIGHTERS/ffmpegsettings.py          ║
# ╚══════════════════════════════════════════════════════════════╝

from pyrogram import Client
from pyrogram import filters as pyro_filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import Config
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.database.mangodb import (
    get_active_userbots,
    get_ffmpeg_settings,
    get_sudo_users,
    save_ffmpeg_settings,
)

log = LOGGER("FFmpeg")


# ──────────────────────────────────────────────────────────────
# AUTH HELPERS
# ──────────────────────────────────────────────────────────────

def is_owner(user_id: int) -> bool:
    return user_id == int(Config.OWNER_ID)


async def is_sudo(user_id: int) -> bool:
    sudos = await get_sudo_users()
    return user_id in sudos


async def is_authorized(user_id: int) -> bool:
    return is_owner(user_id) or await is_sudo(user_id)


# ──────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────

DEFAULT_FFMPEG = {
    "volume":     1.0,
    "compressor": False,
    "limiter":    False,
    "bass":       0,
    "pitch":      "normal",
    "echo":       False,
}

VOL_LABEL = {
    1.0:  "𝟭𝟬𝟬%",
    5.0:  "𝟱𝟬𝟬%",
    20.0: "𝟮𝟬𝟬𝟬%",
    50.0: "𝗠𝗔𝗫 💥",
}

BASS_LABEL = {
    0:  "𝗡𝗼𝗿𝗺𝗮𝗹",
    20: "𝗛𝗲𝗮𝘃𝘆",
    40: "🌍 𝗘𝗮𝗿𝘁𝗵𝗾𝘂𝗮𝗸𝗲",
}

PITCH_LABEL = {
    "normal":   "𝗡𝗼𝗿𝗺𝗮𝗹",
    "demon":    "👹 𝗗𝗲𝗺𝗼𝗻",
    "chipmunk": "🐹 𝗖𝗵𝗶𝗽𝗺𝘂𝗻𝗸",
}


# ──────────────────────────────────────────────────────────────
# PROFILE DETECTOR
# ──────────────────────────────────────────────────────────────

def get_profile(s: dict) -> str:
    """Auto-detect current profile label based on active settings."""
    all_max = (
        s.get("volume", 1.0) >= 50.0
        and s.get("compressor", False)
        and s.get("limiter", False)
        and s.get("bass", 0) >= 40
        and s.get("pitch") == "demon"
        and s.get("echo", False)
    )
    all_default = (
        s.get("volume", 1.0) == 1.0
        and not s.get("compressor", False)
        and not s.get("limiter", False)
        and s.get("bass", 0) == 0
        and s.get("pitch") == "normal"
        and not s.get("echo", False)
    )
    if all_max:
        return "💀 𝗚𝗮𝗮𝗻𝗱 𝗙𝗮𝗮𝗱 𝗠𝗼𝗱𝗲"
    if all_default:
        return "😴 𝗗𝗲𝗳𝗮𝘂𝗹𝘁 𝗠𝗼𝗱𝗲"
    return "⚔️ 𝗖𝘂𝘀𝘁𝗼𝗺 𝗠𝗼𝗱𝗲"


# ──────────────────────────────────────────────────────────────
# FILTER CHAIN BUILDER
# ──────────────────────────────────────────────────────────────

def build_filter_chain(s: dict) -> str | None:
    """
    Builds a single FFmpeg -af filter string from current settings.
    Returns None if no filters are active (clean passthrough).
    """
    chain = []

    vol = s.get("volume", 1.0)
    if vol != 1.0:
        chain.append(f"volume={vol}")

    if s.get("compressor"):
        chain.append("acompressor=ratio=20:makeup=24")

    if s.get("limiter"):
        chain.append("alimiter=limit=-0.5dB")

    bass = s.get("bass", 0)
    if bass != 0:
        chain.append(f"bass=g={bass}")

    pitch = s.get("pitch", "normal")
    if pitch == "demon":
        chain.append("asetrate=44100*0.7,aresample=44100")
    elif pitch == "chipmunk":
        chain.append("asetrate=44100*1.6,aresample=44100")

    if s.get("echo"):
        chain.append("aecho=0.8:0.9:1000:0.3")

    return ",".join(chain) if chain else None


# ──────────────────────────────────────────────────────────────
# PANEL BUILDER
# ──────────────────────────────────────────────────────────────

def build_panel(s: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Returns (text, keyboard) for the FFmpeg panel."""

    profile  = get_profile(s)
    vol_lbl  = VOL_LABEL.get(s.get("volume", 1.0), f"{int(s.get('volume',1.0)*100)}%")
    comp_lbl = "𝙊𝙉 ✅" if s.get("compressor") else "𝙊𝙁𝙁 ❌"
    lim_lbl  = "𝙊𝙉 ✅" if s.get("limiter")    else "𝙊𝙁𝙁 ❌"
    bass_lbl = BASS_LABEL.get(s.get("bass", 0), str(s.get("bass", 0)))
    pitch_lbl = PITCH_LABEL.get(s.get("pitch", "normal"), "𝗡𝗼𝗿𝗺𝗮𝗹")
    echo_lbl = "𝙊𝙉 ✅" if s.get("echo") else "𝙊𝙁𝙁 ❌"

    text = (
        "🛠️ **𝗙𝗙𝗠𝗣𝗘𝗚 𝗪𝗘𝗔𝗣𝗢𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟𝗦** 🛠️\n"
        f"Cᴜʀʀᴇɴᴛ Pʀᴏғɪʟᴇ: {profile}\n\n"
        f"🔊 **𝗩𝗼𝗹𝘂𝗺𝗲:** {vol_lbl}\n"
        f"🎛️ **𝗖𝗼𝗺𝗽𝗿𝗲𝘀𝘀𝗼𝗿:** {comp_lbl}   |   🔒 **𝗟𝗶𝗺𝗶𝘁𝗲𝗿:** {lim_lbl}\n"
        f"🎸 **𝗕𝗮𝘀𝘀:** {bass_lbl}\n"
        f"👹 **𝗣𝗶𝘁𝗰𝗵:** {pitch_lbl}\n"
        f"🦇 **𝗘𝗰𝗵𝗼:** {echo_lbl}"
    )

    # Selected-state markers for current values
    def v_mark(val):  return "✦ " if s.get("volume") == val else ""
    def b_mark(val):  return "✦ " if s.get("bass") == val else ""
    def p_mark(val):  return "✦ " if s.get("pitch") == val else ""

    keyboard = InlineKeyboardMarkup([
        # ── Row 1: Volume ──────────────────────────────────────
        [
            InlineKeyboardButton(f"{v_mark(1.0)}🔊 𝟭𝟬𝟬%",   callback_data="ff_vol_1"),
            InlineKeyboardButton(f"{v_mark(5.0)}🔊 𝟱𝟬𝟬%",   callback_data="ff_vol_5"),
            InlineKeyboardButton(f"{v_mark(20.0)}🔊 𝟮𝟬𝟬𝟬%", callback_data="ff_vol_20"),
            InlineKeyboardButton(f"{v_mark(50.0)}🔊 𝗠𝗔𝗫 💥", callback_data="ff_vol_50"),
        ],
        # ── Row 2: Compressor & Limiter ────────────────────────
        [
            InlineKeyboardButton(
                f"🎛️ 𝗖𝗼𝗺𝗽𝗿𝗲𝘀𝘀𝗼𝗿: {'𝙊𝙁𝙁 ❌' if s.get('compressor') else '𝙊𝙉 ✅'}",
                callback_data="ff_comp",
            ),
            InlineKeyboardButton(
                f"🔒 𝗟𝗶𝗺𝗶𝘁𝗲𝗿: {'𝙊𝙁𝙁 ❌' if s.get('limiter') else '𝙊𝙉 ✅'}",
                callback_data="ff_lim",
            ),
        ],
        # ── Row 3: Bass ────────────────────────────────────────
        [
            InlineKeyboardButton(f"{b_mark(0)}🎸 𝗡𝗼𝗿𝗺𝗮𝗹",       callback_data="ff_bass_0"),
            InlineKeyboardButton(f"{b_mark(20)}🎸 𝗛𝗲𝗮𝘃𝘆",        callback_data="ff_bass_20"),
            InlineKeyboardButton(f"{b_mark(40)}🌍 𝗘𝗮𝗿𝘁𝗵𝗾𝘂𝗮𝗸𝗲", callback_data="ff_bass_40"),
        ],
        # ── Row 4: Pitch ───────────────────────────────────────
        [
            InlineKeyboardButton(f"{p_mark('normal')}👤 𝗡𝗼𝗿𝗺𝗮𝗹",    callback_data="ff_pitch_normal"),
            InlineKeyboardButton(f"{p_mark('demon')}👹 𝗗𝗲𝗺𝗼𝗻",      callback_data="ff_pitch_demon"),
            InlineKeyboardButton(f"{p_mark('chipmunk')}🐹 𝗖𝗵𝗶𝗽𝗺𝘂𝗻𝗸", callback_data="ff_pitch_chipmunk"),
        ],
        # ── Row 5: Echo + Reset ────────────────────────────────
        [
            InlineKeyboardButton(
                f"🦇 𝗘𝗰𝗵𝗼: {'𝙊𝙁𝙁 ❌' if s.get('echo') else '𝙊𝙉 ✅'}",
                callback_data="ff_echo",
            ),
            InlineKeyboardButton("🔄 𝗥𝗲𝘀𝗲𝘁 𝗗𝗲𝗳𝗮𝘂𝗹𝘁𝘀", callback_data="ff_reset"),
        ],
        # ── Row 6: Save ────────────────────────────────────────
        [
            InlineKeyboardButton("💾 𝗦𝗮𝘃𝗲 & 𝗔𝗽𝗽𝗹𝘆 𝘁𝗼 𝗔𝗹𝗹 𝗨𝘀𝗲𝗿𝗯𝗼𝘁𝘀", callback_data="ff_save"),
        ],
        # ── Row 7: Back ────────────────────────────────────────
        [
            InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main"),
        ],
    ])

    return text, keyboard


# ──────────────────────────────────────────────────────────────
# OPEN PANEL (called from Settings.py config_main handler)
# ──────────────────────────────────────────────────────────────

async def open_ffmpeg_panel(client: Client, query: CallbackQuery):
    """Entry point: called when user taps 🛠️ FFmpeg Settings button."""
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return

    s = await get_ffmpeg_settings()
    text, keyboard = build_panel(s)
    await query.edit_message_text(text, reply_markup=keyboard)


# ──────────────────────────────────────────────────────────────
# CALLBACK HANDLER
# ──────────────────────────────────────────────────────────────

from VCFIGHTERS.core.bot import app  # noqa: E402  (imported here to avoid circular)


@app.on_callback_query(pyro_filters.regex(r"^ff_"))
async def ffmpeg_callback_handler(client: Client, query: CallbackQuery):

    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return

    data = query.data
    s    = await get_ffmpeg_settings()

    # ── Volume ──────────────────────────────────────────────────
    if   data == "ff_vol_1":   s["volume"] = 1.0
    elif data == "ff_vol_5":   s["volume"] = 5.0
    elif data == "ff_vol_20":  s["volume"] = 20.0
    elif data == "ff_vol_50":  s["volume"] = 50.0

    # ── Compressor toggle ───────────────────────────────────────
    elif data == "ff_comp":
        s["compressor"] = not s.get("compressor", False)

    # ── Limiter toggle ──────────────────────────────────────────
    elif data == "ff_lim":
        s["limiter"] = not s.get("limiter", False)

    # ── Bass ────────────────────────────────────────────────────
    elif data == "ff_bass_0":   s["bass"] = 0
    elif data == "ff_bass_20":  s["bass"] = 20
    elif data == "ff_bass_40":  s["bass"] = 40

    # ── Pitch ───────────────────────────────────────────────────
    elif data == "ff_pitch_normal":   s["pitch"] = "normal"
    elif data == "ff_pitch_demon":    s["pitch"] = "demon"
    elif data == "ff_pitch_chipmunk": s["pitch"] = "chipmunk"

    # ── Echo toggle ─────────────────────────────────────────────
    elif data == "ff_echo":
        s["echo"] = not s.get("echo", False)

    # ── Reset Defaults ──────────────────────────────────────────
    elif data == "ff_reset":
        s = DEFAULT_FFMPEG.copy()
        await save_ffmpeg_settings(s)
        await query.answer("🔄 𝗥𝗲𝘀𝗲𝘁 𝘁𝗼 𝗗𝗲𝗳𝗮𝘂𝗹𝘁𝘀 ✅", show_alert=False)
        text, keyboard = build_panel(s)
        await query.edit_message_text(text, reply_markup=keyboard)
        return

    # ── Save & Apply ────────────────────────────────────────────
    elif data == "ff_save":
        await save_ffmpeg_settings(s)
        filter_chain = build_filter_chain(s)
        log.info(f"🔧 Filter chain saved: {filter_chain or 'passthrough'}")

        userbots = await get_active_userbots()
        applied  = 0

        for ub in userbots:
            try:
                # Voice.py exposes apply_filters() — restarts stream with new chain
                from VCFIGHTERS.core.call import vc
                await vc.apply_filters(ub, filter_chain)
                applied += 1
            except Exception as e:
                log.warning(f"⚠️ Could not apply filters to {ub.get('phone','?')}: {e}")

        msg = (
            f"✅ 𝗦𝗮𝘃𝗲𝗱 & 𝗔𝗽𝗽𝗹𝗶𝗲𝗱 𝘁𝗼 {applied} 𝘂𝘀𝗲𝗿𝗯𝗼𝘁𝘀"
            if applied else
            "💾 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀 𝗦𝗮𝘃𝗲𝗱 (𝗻𝗼 𝗮𝗰𝘁𝗶𝘃𝗲 𝘀𝘁𝗿𝗲𝗮𝗺𝘀)"
        )
        await query.answer(msg, show_alert=True)
        text, keyboard = build_panel(s)
        await query.edit_message_text(text, reply_markup=keyboard)
        return

    # ── Rebuild panel after any toggle ──────────────────────────
    await query.answer()
    text, keyboard = build_panel(s)
    await query.edit_message_text(text, reply_markup=keyboard)
  
