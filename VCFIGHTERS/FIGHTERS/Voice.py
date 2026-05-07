import asyncio
import os
import time
from typing import Optional

from pyrogram import filters as pyro_filters
from pyrogram.types import Message

from VCFIGHTERS.core.bot import app
from VCFIGHTERS.core.call import vc
from VCFIGHTERS.database.mangodb import (
    get_mode,
    get_primary_target,
    save_recording,
    delete_recording,
)
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.FIGHTERS.sudo import is_authorized, is_owner, is_sudo

log = LOGGER("Voice")

# ─────────────────────────────────────────────────────────────
#  TEMP DIR
# ─────────────────────────────────────────────────────────────

REC_DIR = "recordings"
os.makedirs(REC_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
#  IN-MEMORY STATE
# ─────────────────────────────────────────────────────────────

# { user_id: { "chat_id": int, "recording": bool, "rec_path": str|None } }
_auto_tracking: dict[int, dict] = {}

# { chat_id: file_path }
_dm_current: dict[int, str] = {}


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

async def _get_target_chat_id() -> Optional[int]:
    target = await get_primary_target()
    if not target:
        log.warning("⚠️ No target set. Use /config → Set Target first.")
        return None
    return target["chat_id"]


def _cleanup_old_recording(user_id: int):
    track    = _auto_tracking.get(user_id, {})
    old_path = track.get("rec_path")
    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
            log.info(f"🧹 Old recording deleted: {old_path}")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#  AUTO MODE — RECORDING
# ══════════════════════════════════════════════════════════════

async def _start_recording(user_id: int, chat_id: int) -> str:
    timestamp = int(time.time())
    rec_path  = os.path.join(REC_DIR, f"rec_{user_id}_{timestamp}.ogg")

    await save_recording(rec_path, user_id)

    _auto_tracking[user_id] = {
        "chat_id":   chat_id,
        "recording": True,
        "rec_path":  rec_path,
    }

    log.info(f"🎙️ Recording started → {rec_path}")
    return rec_path


async def _stop_recording(user_id: int) -> Optional[str]:
    track = _auto_tracking.get(user_id)
    if not track or not track.get("recording"):
        return None

    track["recording"] = False
    rec_path = track.get("rec_path")

    if rec_path and os.path.exists(rec_path):
        size = os.path.getsize(rec_path)
        log.info(f"🎙️ Recording stopped → {rec_path} ({size} bytes)")
        return rec_path if size > 0 else None

    return None


# ══════════════════════════════════════════════════════════════
#  AUTO MODE — PARTICIPANT MONITOR
#
#  Call vc.start() ke BAAD register karo.
# ══════════════════════════════════════════════════════════════

async def register_participant_handlers():
    from pytgcalls import filters as call_filters
    from pytgcalls.types import Update

    for session, pytg in vc._instances.items():

        @pytg.on_update(call_filters.participants_change)
        async def _on_participant_change(_, update: Update):

            mode = await get_mode()
            if mode != "auto":
                return

            for participant in update.participants:

                uid = participant.user_id
                if not (is_owner(uid) or await is_sudo(uid)):
                    continue

                chat_id       = update.chat_id
                is_muted      = participant.muted
                track         = _auto_tracking.get(uid, {})
                was_recording = track.get("recording", False)

                # Mic ON → recording shuru
                if not is_muted and not was_recording:
                    log.info(f"🎙️ {uid} mic ON → recording start")
                    _cleanup_old_recording(uid)
                    await _start_recording(uid, chat_id)

                # Mic OFF → recording band, play karo
                elif is_muted and was_recording:
                    log.info(f"🔇 {uid} mic OFF → playing recording")
                    rec_path = await _stop_recording(uid)

                    if not rec_path:
                        log.warning("⚠️ Recording empty, skipping")
                        return

                    # Screen share check
                    screen_sharing = any(
                        p.video_stopped is False
                        for p in update.participants
                        if p.user_id != uid
                    )

                    await vc.play_loop(
                        chat_id   = chat_id,
                        file_path = rec_path,
                        is_video  = screen_sharing,
                    )
                    mode_str = "📺 ᴠιᴅєᴏ+ᴀᴜᴅιᴏ" if screen_sharing else "🔊 ᴀᴜᴅιᴏ ᴏηʟʏ"
                    log.info(f"{mode_str} loop started → chat {chat_id}")

        log.info(f"✅ Participant handler registered → ...{session[-10:]}")


# ══════════════════════════════════════════════════════════════
#  DM MODE — VOICE NOTE HANDLER
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.private & pyro_filters.voice)
async def dm_voice_handler(client, message: Message):
    uid = message.from_user.id

    if not await is_authorized(uid):
        return

    mode = await get_mode()
    if mode != "dm":
        return

    chat_id = await _get_target_chat_id()
    if not chat_id:
        await message.reply(
            "⚠️ **ηᴏ ᴛᴀʀɢєᴛ sєᴛ!**\n"
            "ᴜsє `/config` → `˹ 𝐓ᴀʀɢєᴛ ˼` ғιʀsᴛ."
        )
        return

    log.info(f"📩 Voice note received from {uid} → DM Mode")

    # Download voice note
    timestamp = int(time.time())
    dl_path   = os.path.join(REC_DIR, f"dm_{uid}_{timestamp}.ogg")

    try:
        await message.download(file_name=dl_path)
        log.info(f"⬇️ Downloaded → {dl_path}")
    except Exception as e:
        log.error(f"❌ Download failed: {e}")
        await message.reply("❌ **ᴅᴏᴡηʟᴏᴀᴅ ғᴀιʟєᴅ!** ᴛʀʏ ᴀɢᴀιη.")
        return

    # Delete old DM file
    old_file = _dm_current.get(chat_id)
    if old_file and os.path.exists(old_file) and old_file != dl_path:
        try:
            os.remove(old_file)
        except Exception:
            pass

    _dm_current[chat_id] = dl_path

    # Small settle delay
    await asyncio.sleep(0.5)

    # Replace if already playing, else start fresh
    if chat_id in vc._active_ub:
        log.info(f"🔄 Replacing audio → chat {chat_id}")
        success = await vc.replace_audio(chat_id, dl_path)
    else:
        log.info(f"▶️ Starting DM loop → chat {chat_id}")
        success = await vc.play_loop(chat_id, dl_path)

    if success:
        await message.reply(
            "✅ **ρʟᴀʏιηɢ ιη ᴠᴄ!** *(ʟᴏᴏρ ϻᴏᴅє)*\n"
            "sєηᴅ ᴀηᴏᴛнєʀ ᴠᴏιᴄє ηᴏᴛє ᴛᴏ ʀєρʟᴀᴄє."
        )
    else:
        await message.reply("❌ **ғᴀιʟєᴅ ᴛᴏ ρʟᴀʏ.** ᴄнєᴄᴋ ιғ ᴠᴄ ιs ᴀᴄᴛιᴠє.")


# ══════════════════════════════════════════════════════════════
#  /stop
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("stop") & pyro_filters.group)
async def stop_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return

    chat_id = message.chat.id

    # Auto mode cleanup
    for user_id, track in list(_auto_tracking.items()):
        if track.get("chat_id") == chat_id:
            await _stop_recording(user_id)
            _cleanup_old_recording(user_id)
            _auto_tracking.pop(user_id, None)

    _dm_current.pop(chat_id, None)
    await vc.stop(chat_id)

    await message.reply("⏹️ **sᴛᴏρρєᴅ & ʟєғᴛ ᴠᴄ.**")
    log.info(f"⏹️ /stop by {uid} → chat {chat_id}")


# ══════════════════════════════════════════════════════════════
#  /pause  /resume
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("pause") & pyro_filters.group)
async def pause_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return

    await vc.stop(message.chat.id, leave_vc=False)
    await message.reply("⏸️ **ρᴀᴜsєᴅ.** ᴜsє `/resume` ᴛᴏ ᴄᴏηᴛιηᴜє.")


@app.on_message(pyro_filters.command("resume") & pyro_filters.group)
async def resume_handler(client, message: Message):
    uid = message.from_user.id
    if not await is_authorized(uid):
        return

    chat_id = message.chat.id
    file    = _dm_current.get(chat_id)

    if not file or not os.path.exists(file):
        await message.reply("⚠️ ηᴏᴛнιηɢ ᴛᴏ ʀєsᴜϻє. sєηᴅ ᴀ ᴠᴏιᴄє ηᴏᴛє ғιʀsᴛ.")
        return

    success = await vc.play_loop(chat_id, file)
    if success:
        await message.reply("▶️ **ʀєsᴜϻєᴅ!**")
    else:
        await message.reply("❌ **ғᴀιʟєᴅ ᴛᴏ ʀєsᴜϻє.**")


# ══════════════════════════════════════════════════════════════
#  /vcstatus
# ══════════════════════════════════════════════════════════════

@app.on_message(pyro_filters.command("vcstatus"))
async def vcstatus_handler(client, message: Message):
    if not is_owner(message.from_user.id):
        return

    mode   = await get_mode()
    status = vc.status()
    target = await get_primary_target()

    text = (
        f"⚔️ **ᴠᴄғιɢнᴛєʀ sᴛᴀᴛᴜs**\n\n"
        f"🎮 ϻᴏᴅє: `{mode.upper()}`\n"
        f"📡 ρʏᴛɢᴄᴀʟʟs ιηsᴛᴀηᴄєs: `{status['pytgcalls_instances']}`\n"
        f"▶️ ᴀᴄᴛιᴠє sᴛʀєᴀϻs: `{status['active_streams']}`\n"
        f"🔁 ʟᴏᴏρ ᴄнᴀᴛs: `{status['loop_active_chats']}`\n"
        f"🎯 ᴛᴀʀɢєᴛ: `{target['chat_id'] if target else 'ηᴏᴛ sєᴛ'}`\n"
        f"🎙️ ᴀᴜᴛᴏ ᴛʀᴀᴄᴋιηɢ: `{len(_auto_tracking)} ᴜsєʀ(s)`"
    )

    await message.reply(text)
    
