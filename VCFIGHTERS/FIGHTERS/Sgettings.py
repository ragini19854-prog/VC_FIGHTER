# ╔══════════════════════════════════════════════════════════════╗
# ║         VCFIGHTER — Config Panel & Settings                  ║
# ║         File: VCFIGHTERS/FIGHTERS/Settings.py                ║
# ╚══════════════════════════════════════════════════════════════╝

import asyncio
import time

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
    add_target,
    add_userbot,
    delete_all_userbots,
    delete_userbot,
    get_all_targets,
    get_all_userbots,
    get_pytgcalls_settings,
    get_settings,
    get_sudo_users,
    save_pytgcalls_settings,
    save_settings,
)
from VCFIGHTERS.FIGHTERS.ffmpegsettings import open_ffmpeg_panel

log = LOGGER("Settings")

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

def is_owner(user_id: int) -> bool:
    return user_id == int(Config.OWNER_ID)


async def is_sudo(user_id: int) -> bool:
    return user_id in await get_sudo_users()


async def is_authorized(user_id: int) -> bool:
    return is_owner(user_id) or await is_sudo(user_id)


# ─────────────────────────────────────────────
# CONVERSATION STATE  (in-memory, per user)
# ─────────────────────────────────────────────

_state: dict[int, dict] = {}   # {user_id: {"step": ..., "data": ...}}


def set_state(uid: int, step: str, **data):
    _state[uid] = {"step": step, **data}


def get_state(uid: int) -> dict:
    return _state.get(uid, {})


def clear_state(uid: int):
    _state.pop(uid, None)


# ─────────────────────────────────────────────
# IMPORT BOT APP
# ─────────────────────────────────────────────

from VCFIGHTERS.core.bot import app  # noqa: E402


# ══════════════════════════════════════════════
#  /config  — MAIN PANEL
# ══════════════════════════════════════════════

def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 𝗦𝗲𝘁 𝗟𝗼𝗴𝗴𝗲𝗿",       callback_data="cfg_logger"),
            InlineKeyboardButton("🛠️ 𝗙𝗙𝗺𝗽𝗲𝗴 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", callback_data="cfg_ffmpeg"),
        ],
        [
            InlineKeyboardButton("🎮 𝗦𝗲𝘁 𝗠𝗼𝗱𝗲",         callback_data="cfg_mode"),
            InlineKeyboardButton("👥 𝗨𝗦𝗘𝗥𝗕𝗢𝗧𝘀",          callback_data="cfg_ub_page_0"),
        ],
        [
            InlineKeyboardButton("🎯 𝗦𝗲𝘁 𝗧𝗮𝗿𝗴𝗲𝘁",        callback_data="cfg_target"),
            InlineKeyboardButton("📡 𝗣𝘆𝗧𝗴𝗖𝗮𝗹𝗹𝘀",          callback_data="cfg_pytgcalls"),
        ],
        [
            InlineKeyboardButton("🏓 𝗣𝗶𝗻𝗴𝘀",              callback_data="cfg_pings"),
        ],
    ])


@app.on_message(pyro_filters.command("config") & pyro_filters.private)
async def cmd_config(client: Client, message: Message):
    if not await is_authorized(message.from_user.id):
        return
    await message.reply(
        "⚙️ **𝗩𝗖𝗙𝗜𝗚𝗛𝗧𝗘𝗥 𝗖𝗢𝗡𝗙𝗜𝗚 𝗣𝗔𝗡𝗘𝗟**",
        reply_markup=_main_menu_kb(),
    )


@app.on_callback_query(pyro_filters.regex("^config_main$"))
async def cb_config_main(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    clear_state(query.from_user.id)
    await query.edit_message_text(
        "⚙️ **𝗩𝗖𝗙𝗜𝗚𝗛𝗧𝗘𝗥 𝗖𝗢𝗡𝗙𝗜𝗚 𝗣𝗔𝗡𝗘𝗟**",
        reply_markup=_main_menu_kb(),
    )


# ══════════════════════════════════════════════
#  BUTTON 1 — FFmpeg  (delegates to ffmpegsettings.py)
# ══════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_ffmpeg$"))
async def cb_ffmpeg(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    await open_ffmpeg_panel(client, query)


# ══════════════════════════════════════════════
#  BUTTON 2 — Set Logger
# ══════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_logger$"))
async def cb_logger(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    set_state(query.from_user.id, "await_logger_chat")
    await query.edit_message_text(
        "📋 **𝗦𝗲𝘁 𝗟𝗼𝗴𝗴𝗲𝗿 𝗖𝗵𝗮𝘁**\n\n"
        "Send the **Chat ID** where logs should be sent.\n"
        "_(Forward any message from that chat or paste the ID directly)_",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")]
        ]),
    )


# ══════════════════════════════════════════════
#  BUTTON 3 — Set Mode
# ══════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_mode$"))
async def cb_mode(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    s = await get_settings()
    cur = s.get("mode", "none")
    await query.edit_message_text(
        f"🎮 **𝗦𝗘𝗟𝗘𝗖𝗧 𝗠𝗢𝗗𝗘**\n\nCurrent: `{cur}`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 𝗔𝘂𝘁𝗼 𝗠𝗼𝗱𝗲", callback_data="cfg_mode_auto"),
                InlineKeyboardButton("🔵 𝗗𝗠 𝗠𝗼𝗱𝗲",   callback_data="cfg_mode_dm"),
            ],
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")],
        ]),
    )


@app.on_callback_query(pyro_filters.regex("^cfg_mode_(auto|dm)$"))
async def cb_mode_set(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    mode = query.data.split("_")[-1]
    await save_settings({"mode": mode})
    await query.answer(f"✅ Mode set to {mode.upper()}", show_alert=False)
    await query.edit_message_text(
        f"🎮 **𝗦𝗘𝗟𝗘𝗖𝗧 𝗠𝗢𝗗𝗘**\n\nCurrent: `{mode}`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 𝗔𝘂𝘁𝗼 𝗠𝗼𝗱𝗲", callback_data="cfg_mode_auto"),
                InlineKeyboardButton("🔵 𝗗𝗠 𝗠𝗼𝗱𝗲",   callback_data="cfg_mode_dm"),
            ],
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")],
        ]),
    )


# ══════════════════════════════════════════════
#  BUTTON 4 — USERBOTs Manager
# ══════════════════════════════════════════════

def _ub_panel(userbots: list, page: int) -> tuple[str, InlineKeyboardMarkup]:
    total = len(userbots)
    if total == 0:
        text = "👥 **𝗨𝗦𝗘𝗥𝗕𝗢𝗧𝗦 𝗠𝗔𝗡𝗔𝗚𝗘𝗥**\n\nNo userbots added yet."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ 𝗦𝗲𝘁 𝗦𝘁𝗿𝗶𝗻𝗴 𝗦𝗲𝘀𝘀𝗶𝗼𝗻", callback_data="cfg_ub_add_menu")],
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")],
        ])
        return text, kb

    ub   = userbots[page]
    phone  = ub.get("phone", "𝗨𝗻𝗸𝗻𝗼𝘄𝗻")
    status = "✅ 𝗔𝗰𝘁𝗶𝘃𝗲" if ub.get("active") else "❌ 𝗜𝗻𝗮𝗰𝘁𝗶𝘃𝗲"

    text = (
        f"👥 **𝗨𝗦𝗘𝗥𝗕𝗢𝗧𝗦 𝗠𝗔𝗡𝗔𝗚𝗘𝗥**\n\n"
        f"𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝗯𝗼𝘁𝘀: {total}\n\n"
        f"📱 `{phone}`  |  {status}"
    )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ 𝗣𝗿𝗲𝘃", callback_data=f"cfg_ub_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"𝗨𝘀𝗲𝗿𝗯𝗼𝘁 {page+1} 𝗼𝗳 {total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"cfg_ub_page_{page+1}"))

    kb = InlineKeyboardMarkup([
        nav,
        [InlineKeyboardButton("➕ 𝗦𝗲𝘁 𝗦𝘁𝗿𝗶𝗻𝗴 𝗦𝗲𝘀𝘀𝗶𝗼𝗻", callback_data="cfg_ub_add_menu")],
        [
            InlineKeyboardButton("❌ 𝗗𝗲𝗹 𝗧𝗵𝗶𝘀",  callback_data=f"cfg_ub_del_{page}"),
            InlineKeyboardButton("🗑️ 𝗗𝗲𝗹𝗲𝘁𝗲 𝗔𝗹𝗹", callback_data="cfg_ub_delall"),
        ],
        [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")],
    ])
    return text, kb


@app.on_callback_query(pyro_filters.regex(r"^cfg_ub_page_(\d+)$"))
async def cb_ub_page(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    page = int(query.data.split("_")[-1])
    ubs  = await get_all_userbots()
    text, kb = _ub_panel(ubs, min(page, max(0, len(ubs)-1)))
    await query.edit_message_text(text, reply_markup=kb)


@app.on_callback_query(pyro_filters.regex("^cfg_ub_add_menu$"))
async def cb_ub_add_menu(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    await query.edit_message_text(
        "➕ **𝗔𝗱𝗱 𝗨𝘀𝗲𝗿𝗯𝗼𝘁**\n\nChoose how to add:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 𝗕𝘆 𝗣𝗵𝗼𝗻𝗲 𝗡𝘂𝗺𝗯𝗲𝗿", callback_data="cfg_ub_by_phone")],
            [InlineKeyboardButton("🖊️ 𝗦𝗲𝘁 𝗠𝗮𝗻𝘂𝗮𝗹𝗹𝘆",      callback_data="cfg_ub_manual")],
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="cfg_ub_page_0")],
        ]),
    )


# ── By Phone Number ──────────────────────────────────────────

@app.on_callback_query(pyro_filters.regex("^cfg_ub_by_phone$"))
async def cb_ub_by_phone(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    set_state(query.from_user.id, "await_phone")
    await query.edit_message_text(
        "📱 **𝗕𝘆 𝗣𝗵𝗼𝗻𝗲 𝗡𝘂𝗺𝗯𝗲𝗿**\n\n"
        "Send the phone number with country code:\n`+91XXXXXXXXXX`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="cfg_ub_add_menu")]
        ]),
    )


# ── Manual Session ───────────────────────────────────────────

@app.on_callback_query(pyro_filters.regex("^cfg_ub_manual$"))
async def cb_ub_manual(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    set_state(query.from_user.id, "await_session_string")
    await query.edit_message_text(
        "🖊️ **𝗦𝗲𝘁 𝗠𝗮𝗻𝘂𝗮𝗹𝗹𝘆**\n\nPaste the **String Session** below:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="cfg_ub_add_menu")]
        ]),
    )


@app.on_message(pyro_filters.command("setsession") & pyro_filters.private)
async def cmd_setsession(client: Client, message: Message):
    if not await is_authorized(message.from_user.id):
        return
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply("Usage: `/setsession <string_session>`")
        return
    session = parts[1].strip()
    await _save_manual_session(client, message, session, message.from_user.id)


async def _save_manual_session(client, msg_or_query, session: str, user_id: int):
    try:
        from pyrogram import Client as PyroClient
        tmp = PyroClient(
            name="tmp_verify",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            session_string=session,
            no_updates=True,
        )
        await tmp.start()
        me = await tmp.get_me()
        phone = me.phone_number or "Unknown"
        await tmp.stop()
    except Exception as e:
        err = f"❌ Invalid session: `{e}`"
        if isinstance(msg_or_query, Message):
            await msg_or_query.reply(err)
        else:
            await msg_or_query.edit_message_text(err)
        return

    await add_userbot({
        "session_string": session,
        "phone": phone,
        "added_by": user_id,
        "added_at": int(time.time()),
        "active": True,
    })

    # Start the new userbot client
    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.start_userbot(session)
    except Exception as e:
        log.warning(f"Userbot started in DB but client failed: {e}")

    ok = f"✅ Userbot `{phone}` added & started!"
    if isinstance(msg_or_query, Message):
        await msg_or_query.reply(ok)
    else:
        await msg_or_query.edit_message_text(ok, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="cfg_ub_page_0")]
        ]))


# ── Delete This / Delete All ─────────────────────────────────

@app.on_callback_query(pyro_filters.regex(r"^cfg_ub_del_(\d+)$"))
async def cb_ub_del(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    page = int(query.data.split("_")[-1])
    ubs  = await get_all_userbots()
    if not ubs or page >= len(ubs):
        await query.answer("No userbot at this index.", show_alert=True)
        return
    ub = ubs[page]
    await delete_userbot(ub["session_string"])
    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.stop_userbot(ub["session_string"])
    except Exception: pass
    await query.answer(f"🗑️ Userbot {ub.get('phone','?')} deleted.", show_alert=False)
    ubs = await get_all_userbots()
    new_page = min(page, max(0, len(ubs)-1))
    text, kb = _ub_panel(ubs, new_page)
    await query.edit_message_text(text, reply_markup=kb)


@app.on_callback_query(pyro_filters.regex("^cfg_ub_delall$"))
async def cb_ub_delall(client: Client, query: CallbackQuery):
    if not is_owner(query.from_user.id):
        await query.answer("⛔ 𝗢𝘄𝗻𝗲𝗿 𝗢𝗻𝗹𝘆", show_alert=True)
        return
    await delete_all_userbots()
    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.stop_all()
    except Exception: pass
    await query.answer("🗑️ All userbots deleted.", show_alert=True)
    text, kb = _ub_panel([], 0)
    await query.edit_message_text(text, reply_markup=kb)


# ══════════════════════════════════════════════
#  BUTTON 5 — Set Target
# ══════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_target$"))
async def cb_target(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    targets = await get_all_targets()
    await _show_targets(query, targets, page=0, ask_new=True)


async def _show_targets(query: CallbackQuery, targets: list, page: int, ask_new: bool = False):
    total = len(targets)
    if total == 0 or ask_new:
        set_state(query.from_user.id, "await_target_link")
        await query.edit_message_text(
            "🎯 **𝗦𝗲𝘁 𝗧𝗮𝗿𝗴𝗲𝘁**\n\n"
            "Send the **Group Invite Link**:\n`t.me/+xxxx` or `t.me/joinchat/xxxx`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")]
            ]),
        )
        return

    t     = targets[page]
    chat  = t.get("chat_id", "𝗡/𝗔")
    link  = t.get("invite_link", "")
    joined = len(t.get("userbots_joined", []))
    text  = (
        f"🎯 **𝗦𝗘𝗧 𝗧𝗔𝗥𝗚𝗘𝗧**\n\n"
        f"𝗖𝗵𝗮𝘁 𝗜𝗗: `{chat}`\n"
        f"𝗟𝗶𝗻𝗸: {link}\n"
        f"𝗨𝘀𝗲𝗿𝗯𝗼𝘁𝘀 𝗝𝗼𝗶𝗻𝗲𝗱: {joined}"
    )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ 𝗣𝗿𝗲𝘃", callback_data=f"cfg_tgt_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"cfg_tgt_page_{page+1}"))

    kb = InlineKeyboardMarkup([
        nav,
        [InlineKeyboardButton("➕ 𝗔𝗱𝗱 𝗡𝗲𝘄 𝗧𝗮𝗿𝗴𝗲𝘁", callback_data="cfg_target_new")],
        [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")],
    ])
    await query.edit_message_text(text, reply_markup=kb)


@app.on_callback_query(pyro_filters.regex(r"^cfg_tgt_page_(\d+)$"))
async def cb_tgt_page(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    page = int(query.data.split("_")[-1])
    targets = await get_all_targets()
    await _show_targets(query, targets, page)


@app.on_callback_query(pyro_filters.regex("^cfg_target_new$"))
async def cb_target_new(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    set_state(query.from_user.id, "await_target_link")
    await query.edit_message_text(
        "🎯 **𝗦𝗲𝘁 𝗧𝗮𝗿𝗴𝗲𝘁**\n\n"
        "Send the **Group Invite Link**:\n`t.me/+xxxx` or `t.me/joinchat/xxxx`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")]
        ]),
    )


# ══════════════════════════════════════════════
#  BUTTON 6 — PyTgCalls Settings
# ══════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_pytgcalls$"))
async def cb_pytgcalls(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    s = await get_pytgcalls_settings()
    await _show_pytg_panel(query, s)


async def _show_pytg_panel(query: CallbackQuery, s: dict):
    st  = s.get("stream_type", "audio")
    ql  = s.get("quality",     "medium")
    ns  = s.get("noise_suppression", False)

    def mk(label, cd, active): return InlineKeyboardButton(
        ("✦ " if active else "") + label, callback_data=cd
    )

    kb = InlineKeyboardMarkup([
        [
            mk("🔊 𝗔𝘂𝗱𝗶𝗼 𝗢𝗻𝗹𝘆",     "cfg_ptg_st_audio", st == "audio"),
            mk("🎥 𝗔𝘂𝗱𝗶𝗼 + 𝗩𝗶𝗱𝗲𝗼", "cfg_ptg_st_video", st == "video"),
        ],
        [
            mk("𝗟𝗼𝘄",    "cfg_ptg_ql_low",    ql == "low"),
            mk("𝗠𝗲𝗱𝗶𝘂𝗺", "cfg_ptg_ql_medium", ql == "medium"),
            mk("𝗛𝗶𝗴𝗵",   "cfg_ptg_ql_high",   ql == "high"),
        ],
        [
            InlineKeyboardButton(
                f"🔇 𝗡𝗼𝗶𝘀𝗲 𝗦𝘂𝗽𝗽𝗿𝗲𝘀𝘀𝗶𝗼𝗻: {'𝙊𝙉 ✅' if ns else '𝙊𝙁𝙁 ❌'}",
                callback_data="cfg_ptg_ns",
            )
        ],
        [InlineKeyboardButton("💾 𝗦𝗮𝘃𝗲 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", callback_data="cfg_ptg_save")],
        [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main")],
    ])
    text = (
        "📡 **𝗣𝗬𝗧𝗚𝗖𝗔𝗟𝗟𝗦 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦**\n\n"
        f"𝗦𝘁𝗿𝗲𝗮𝗺 𝗧𝘆𝗽𝗲: `{st}`\n"
        f"𝗤𝘂𝗮𝗹𝗶𝘁𝘆: `{ql}`\n"
        f"𝗡𝗼𝗶𝘀𝗲 𝗦𝘂𝗽𝗽𝗿𝗲𝘀𝘀𝗶𝗼𝗻: `{'ON' if ns else 'OFF'}`"
    )
    await query.edit_message_text(text, reply_markup=kb)


@app.on_callback_query(pyro_filters.regex(r"^cfg_ptg_(st|ql|ns|save)"))
async def cb_pytg_toggle(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    s   = await get_pytgcalls_settings()
    d   = query.data

    if   d == "cfg_ptg_st_audio":  s["stream_type"] = "audio"
    elif d == "cfg_ptg_st_video":  s["stream_type"] = "video"
    elif d == "cfg_ptg_ql_low":    s["quality"] = "low"
    elif d == "cfg_ptg_ql_medium": s["quality"] = "medium"
    elif d == "cfg_ptg_ql_high":   s["quality"] = "high"
    elif d == "cfg_ptg_ns":        s["noise_suppression"] = not s.get("noise_suppression", False)
    elif d == "cfg_ptg_save":
        await save_pytgcalls_settings(s)
        await query.answer("💾 𝗦𝗮𝘃𝗲𝗱 ✅", show_alert=False)

    await _show_pytg_panel(query, s)


# ══════════════════════════════════════════════
#  BUTTON 7 — Pings
# ══════════════════════════════════════════════

@app.on_callback_query(pyro_filters.regex("^cfg_pings$"))
async def cb_pings(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    await _show_pings(query)


@app.on_callback_query(pyro_filters.regex("^cfg_pings_refresh$"))
async def cb_pings_refresh(client: Client, query: CallbackQuery):
    if not await is_authorized(query.from_user.id):
        await query.answer("⛔ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱", show_alert=True)
        return
    await _show_pings(query)


async def _show_pings(query: CallbackQuery):
    from VCFIGHTERS.database.mangodb import db

    # Bot ping
    t0 = time.monotonic()
    await query.answer()
    bot_ms = int((time.monotonic() - t0) * 1000)

    # MongoDB ping
    try:
        t0 = time.monotonic()
        await db.command("ping")
        mongo_ms = int((time.monotonic() - t0) * 1000)
        mongo_str = f"{mongo_ms}ms"
    except Exception:
        mongo_str = "❌ Dead"

    # Userbot pings
    ubs = await get_all_userbots()
    ub_lines = []
    for i, ub in enumerate(ubs, 1):
        try:
            from VCFIGHTERS.core.userbot import userbot_manager
            ub_client = userbot_manager.get_client(ub["session_string"])
            t0 = time.monotonic()
            await ub_client.get_me()
            ms = int((time.monotonic() - t0) * 1000)
            ub_lines.append(f"👤 𝗨𝘀𝗲𝗿𝗯𝗼𝘁 {i}:      {ms}ms ✅")
        except Exception:
            ub_lines.append(f"👤 𝗨𝘀𝗲𝗿𝗯𝗼𝘁 {i}:      ❌ Dead")

    ub_text = "\n".join(ub_lines) if ub_lines else "_(No userbots added)_"

    text = (
        "🏓 **𝗦𝗬𝗦𝗧𝗘𝗠 𝗣𝗜𝗡𝗚𝗦**\n\n"
        f"🤖 𝗕𝗼𝘁 𝗦𝗲𝗿𝘃𝗲𝗿:     {bot_ms}ms\n"
        f"🗄️ 𝗠𝗼𝗻𝗴𝗼𝗗𝗕:        {mongo_str}\n"
        f"{ub_text}"
    )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵",  callback_data="cfg_pings_refresh"),
                InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="config_main"),
            ]
        ]),
    )


# ══════════════════════════════════════════════
#  MESSAGE HANDLER — Conversation Flow
# ══════════════════════════════════════════════

@app.on_message(pyro_filters.private & ~pyro_filters.command([
    "start", "config", "setsession", "addsudo", "delsudo", "sudolist"
]))
async def conversation_handler(client: Client, message: Message):
    uid   = message.from_user.id
    state = get_state(uid)
    step  = state.get("step")

    if not step:
        return

    # ── Logger chat ────────────────────────────────────────────
    if step == "await_logger_chat":
        try:
            chat_id = int(message.text.strip())
            await client.send_message(chat_id, "✅ Logger connected!")
            await save_settings({"logger_chat": chat_id})
            clear_state(uid)
            await message.reply(
                f"✅ Logger set to `{chat_id}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗖𝗼𝗻𝗳𝗶𝗴", callback_data="config_main")]
                ]),
            )
        except Exception as e:
            await message.reply(f"❌ Failed: `{e}`\nTry again or press Back.")

    # ── Phone number for new userbot ───────────────────────────
    elif step == "await_phone":
        phone = message.text.strip()
        set_state(uid, "await_otp", phone=phone)
        try:
            from pyrogram import Client as PyroClient
            tmp = PyroClient(
                "tmp_login",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
            )
            await tmp.connect()
            sent = await tmp.send_code(phone)
            set_state(uid, "await_otp", phone=phone, phone_code_hash=sent.phone_code_hash, tmp=tmp)
            await message.reply(
                f"📲 OTP sent to `{phone}`\n\nSend the OTP now:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ 𝗖𝗮𝗻𝗰𝗲𝗹", callback_data="config_main")]
                ]),
            )
        except Exception as e:
            clear_state(uid)
            await message.reply(f"❌ Error sending OTP: `{e}`")

    # ── OTP for phone login ────────────────────────────────────
    elif step == "await_otp":
        otp   = message.text.strip().replace(" ", "")
        phone = state.get("phone")
        hash_ = state.get("phone_code_hash")
        tmp   = state.get("tmp")
        try:
            await tmp.sign_in(phone, hash_, otp)
            session = await tmp.export_session_string()
            me      = await tmp.get_me()
            await tmp.stop()
            clear_state(uid)
            await _save_manual_session(client, message, session, uid)
        except Exception as e:
            await message.reply(f"❌ OTP error: `{e}`\nTry again:")

    # ── Manual session string ──────────────────────────────────
    elif step == "await_session_string":
        session = message.text.strip()
        clear_state(uid)
        await _save_manual_session(client, message, session, uid)

    # ── Target invite link ─────────────────────────────────────
    elif step == "await_target_link":
        link = message.text.strip()
        if "t.me/+" not in link and "joinchat" not in link:
            await message.reply("❌ Invalid link. Send a valid group invite link.")
            return
        clear_state(uid)
        await message.reply("⏳ Joining with all userbots...")

        ubs     = await get_all_userbots()
        joined  = []
        chat_id = None

        from VCFIGHTERS.core.userbot import userbot_manager

        for ub in ubs:
            try:
                ub_client = userbot_manager.get_client(ub["session_string"])
                chat      = await ub_client.join_chat(link)
                chat_id   = chat.id
                joined.append(ub.get("phone", "?"))
                await asyncio.sleep(3)
            except Exception as e:
                log.warning(f"Userbot {ub.get('phone')} join failed: {e}")

        if chat_id:
            await add_target({
                "chat_id": chat_id,
                "invite_link": link,
                "userbots_joined": joined,
                "added_at": int(time.time()),
            })
            await message.reply(
                f"✅ `{len(joined)}` userbots joined.\n"
                f"🎯 Target saved: `{chat_id}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗖𝗼𝗻𝗳𝗶𝗴", callback_data="config_main")]
                ]),
            )
        else:
            await message.reply("❌ No userbots could join. Check the invite link.")
