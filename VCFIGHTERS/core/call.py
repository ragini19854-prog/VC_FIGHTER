Import asyncio
from typing import Optional

from pytgcalls import PyTgCalls
from pytgcalls import filters as call_filters
from pytgcalls.types import AudioQuality, MediaStream, Update, VideoQuality

from VCFIGHTERS.database.mangodb import (
    get_ffmpeg_settings,
    get_pytgcalls_settings,
)
from VCFIGHTERS.logging import LOGGER

log = LOGGER("VCCall")


# ══════════════════════════════════════════════════════════════
#  FFMPEG FILTER BUILDER
#
#  DB se settings padhke ek -af filter string banata hai.
#  Ye string directly MediaStream ke
#  additional_ffmpeg_parameters mein jaati hai.
#
#  Live piping:
#    PyTgCalls khud FFmpeg chalata hai internally.
#    Hum sirf filters pass karte hain.
#    Bot 1 second mein VC join karta hai —
#    FFmpeg live chalate-chalate process karta hai.
#    Koi temp file nahi banta.
# ══════════════════════════════════════════════════════════════

async def build_ffmpeg_parameters() -> str:
    """
    DB se FFmpeg settings padhke ready-to-use
    additional_ffmpeg_parameters string return karta hai.

    Example return value:
        "-af volume=20.0,acompressor=ratio=20:makeup=24,bass=g=40"

    Agar koi filter enable nahi → "" (empty string) return hoga.
    """
    cfg     = await get_ffmpeg_settings()
    filters = []

    # ── 1. Volume ──────────────────────────────
    vol = cfg.get("volume", 1.0)
    if vol != 1.0:
        filters.append(f"volume={vol}")

    # ── 2. Compressor ──────────────────────────
    if cfg.get("compressor", False):
        filters.append("acompressor=ratio=20:makeup=24")

    # ── 3. Brickwall Limiter ───────────────────
    if cfg.get("limiter", False):
        filters.append("alimiter=limit=-0.5dB")

    # ── 4. Bass Boost ──────────────────────────
    bass = cfg.get("bass", 0)
    if bass and bass != 0:
        filters.append(f"bass=g={bass}")

    # ── 5. Pitch ───────────────────────────────
    pitch = cfg.get("pitch", "normal")
    if pitch == "demon":
        # Aawaz moti aur khaufnak
        filters.append("asetrate=44100*0.7,aresample=44100")
    elif pitch == "chipmunk":
        # Aawaz patli aur troll mode
        filters.append("asetrate=44100*1.6,aresample=44100")

    # ── 6. Echo / Reverb ───────────────────────
    if cfg.get("echo", False):
        filters.append("aecho=0.8:0.9:1000:0.3")

    if not filters:
        return ""  # Koi filter nahi → PyTgCalls default use karega

    return f"-af {','.join(filters)}"


# ══════════════════════════════════════════════════════════════
#  VCCall — Main PyTgCalls Manager
#
#  Har userbot ke liye alag PyTgCalls instance manage karta hai.
#
#  Loop accuracy:
#    on_stream_end event har instance mein register hota hai.
#    Jaise hi audio exact khatam hota hai → turant dubara play.
#    Koi sleep nahi, koi jugaad nahi.
# ══════════════════════════════════════════════════════════════

class VCCall:

    def __init__(self):
        # session_string → PyTgCalls instance
        self._instances: dict[str, PyTgCalls] = {}

        # chat_id → (file_path, is_video)
        # None hone ka matlab: loop mode OFF hai is chat mein
        self._loop_data: dict[int, tuple[str, bool]] = {}

        # chat_id → session_string (konsa userbot is chat mein active)
        self._active_ub: dict[int, str] = {}

        log.info("⚙️ VCCall manager initialized")

    # ──────────────────────────────────────────
    #  START — Startup pe call hoga
    # ──────────────────────────────────────────

    async def start(self):
        """
        __main__.py se startup pe call hota hai.
        UserbotManager ke saare active clients ke liye
        PyTgCalls instances banata hai.
        """
        from VCFIGHTERS.core.userbot import userbot_manager

        sessions = userbot_manager.get_all_sessions()
        clients  = userbot_manager.get_all_clients()

        if not clients:
            log.warning("⚠️ No userbots found — PyTgCalls not started")
            return

        for session, client in zip(sessions, clients):
            await self._init_instance(session, client)

        log.info(f"✅ PyTgCalls started for {len(self._instances)} userbot(s)")

    # ──────────────────────────────────────────
    #  INIT INSTANCE — Ek userbot ke liye
    # ──────────────────────────────────────────

    async def _init_instance(self, session: str, client) -> PyTgCalls:
        """
        Ek userbot client ke liye PyTgCalls banao,
        on_stream_end handler register karo, aur start karo.
        """
        if session in self._instances:
            return self._instances[session]

        pytg = PyTgCalls(client)

        # ── on_stream_end: Jaise hi audio khatam ho → loop check ──
        # Ye closure session aur pytg ko capture karta hai
        @pytg.on_update(call_filters.stream_end)
        async def _on_stream_end(_, update: Update):
            chat_id = update.chat_id

            # Kya ye chat loop mode mein hai?
            loop_info = self._loop_data.get(chat_id)
            if not loop_info:
                # Loop mode OFF — track hata do
                log.info(f"⏹️ Stream ended (no loop) → chat {chat_id}")
                self._active_ub.pop(chat_id, None)
                return

            file_path, is_video = loop_info
            log.info(f"🔁 Stream ended → looping again → chat {chat_id}")

            # Turant dobara chalao — koi delay nahi
            await self._do_play(
                pytg      = pytg,
                chat_id   = chat_id,
                session   = session,
                file_path = file_path,
                is_video  = is_video,
                loop      = True,
            )

        await pytg.start()
        self._instances[session] = pytg
        log.info(f"📡 PyTgCalls ready → session ...{session[-10:]}")
        return pytg

    # ──────────────────────────────────────────
    #  ADD / REMOVE USERBOT (Dynamic)
    # ──────────────────────────────────────────

    async def add_userbot(self, session: str, client):
        """
        Naya userbot Settings panel se add hone pe.
        Uske liye PyTgCalls instance dynamically banao.
        """
        pytg = await self._init_instance(session, client)
        log.info(f"➕ Userbot added to VCCall → ...{session[-10:]}")
        return pytg

    def remove_userbot(self, session: str):
        """Userbot delete hone pe uska instance hata do."""
        self._instances.pop(session, None)
        log.info(f"🗑️ PyTgCalls instance removed → ...{session[-10:]}")

    # ──────────────────────────────────────────
    #  INTERNAL: _do_play
    #  Asli play logic — sab methods yahi call karte hain
    # ──────────────────────────────────────────

    async def _do_play(
        self,
        pytg:      PyTgCalls,
        chat_id:   int,
        session:   str,
        file_path: str,
        is_video:  bool = False,
        loop:      bool = False,
    ) -> bool:
        """
        Core play function.

        Live Piping (Zero Delay):
          - FFmpeg filters additional_ffmpeg_parameters se pass hoti hain
          - PyTgCalls internally FFmpeg chalata hai
          - Bot turant VC join karta hai
          - FFmpeg gaana chalate-chalate live process karta hai
          - Koi temp file nahi banta — disk safe
        """
        # DB se live filter string build karo
        ffmpeg_params = await build_ffmpeg_parameters()

        # PyTgCalls quality settings
        pytg_cfg      = await get_pytgcalls_settings()
        quality_str   = pytg_cfg.get("quality", "medium")
        audio_quality = {
            "low":    AudioQuality.STUDIO,
            "medium": AudioQuality.STUDIO,
            "high":   AudioQuality.STUDIO,
        }.get(quality_str, AudioQuality.STUDIO)

        try:
            if is_video:
                # ── Video + Audio (Screen Share) ──────────
                stream = MediaStream(
                    audio_path                   = file_path,
                    video_path                   = "VCFIGHTERS/Assists/Screenshare.mp3",
                    audio_parameters             = audio_quality,
                    video_parameters             = VideoQuality.HD_720p,
                    additional_ffmpeg_parameters = ffmpeg_params,
                )
            else:
                # ── Audio Only ────────────────────────────
                stream = MediaStream(
                    media_path                   = file_path,
                    audio_parameters             = audio_quality,
                    additional_ffmpeg_parameters = ffmpeg_params,
                )

            await pytg.play(chat_id, stream)
            self._active_ub[chat_id] = session

            mode_str = "🔁 loop" if loop else "▶️ once"
            log.info(
                f"{mode_str} | chat={chat_id} | "
                f"file={file_path} | filters={ffmpeg_params or 'none'}"
            )
            return True

        except Exception as e:
            log.error(f"❌ Play failed → chat {chat_id}: {e}")
            return False

    # ──────────────────────────────────────────
    #  PLAY — Ek baar (no loop)
    # ──────────────────────────────────────────

    async def play(
        self,
        chat_id:   int,
        file_path: str,
        session:   Optional[str] = None,
        is_video:  bool = False,
    ) -> bool:
        """
        Ek baar play karo. Khatam hone ke baad VC chhod do.
        FFmpeg filters live apply honge — koi delay nahi.
        """
        pytg, ses = self._resolve(session)
        if not pytg:
            return False

        # Loop mode OFF karo agar pehle se tha
        self._loop_data.pop(chat_id, None)

        return await self._do_play(
            pytg      = pytg,
            chat_id   = chat_id,
            session   = ses,
            file_path = file_path,
            is_video  = is_video,
            loop      = False,
        )

    # ──────────────────────────────────────────
    #  PLAY LOOP — Infinite loop
    # ──────────────────────────────────────────

    async def play_loop(
        self,
        chat_id:   int,
        file_path: str,
        session:   Optional[str] = None,
        is_video:  bool = False,
    ) -> bool:
        """
        file_path ko infinite loop mein play karo.

        Loop accuracy:
          on_stream_end event fire hote hi → turant dobara chalata hai.
          Koi asyncio.sleep nahi. Koi estimate nahi.
          Audio exactly khatam ho → exactly restart ho.
        """
        pytg, ses = self._resolve(session)
        if not pytg:
            return False

        # Loop mode ON karo — on_stream_end handler yahan se padhega
        self._loop_data[chat_id] = (file_path, is_video)

        return await self._do_play(
            pytg      = pytg,
            chat_id   = chat_id,
            session   = ses,
            file_path = file_path,
            is_video  = is_video,
            loop      = True,
        )

    # ──────────────────────────────────────────
    #  REPLACE AUDIO — DM Mode ke liye
    # ──────────────────────────────────────────

    async def replace_audio(
        self,
        chat_id:  int,
        new_file: str,
        session:  Optional[str] = None,
    ) -> bool:
        """
        DM Mode:
          Naya voice note aaya → pehla rok ke naya loop mein chalao.
          VC nahi chhodta — directly audio replace hoti hai.
        """
        log.info(f"🔄 Replacing audio → chat {chat_id}")

        # Pehle loop data clear karo (on_stream_end ab loop nahi karega)
        self._loop_data.pop(chat_id, None)

        # Naya loop start karo
        return await self.play_loop(chat_id, new_file, session)

    # ──────────────────────────────────────────
    #  STOP — VC chhod do
    # ──────────────────────────────────────────

    async def stop(self, chat_id: int, leave_vc: bool = True):
        """
        Loop band karo + optionally VC chhod do.

        leave_vc=False → VC mein rehna hai, sirf audio switch karna hai
        leave_vc=True  → /stop command — VC bilkul chhod do
        """
        # Loop data clear karo (on_stream_end ab loop nahi karega)
        self._loop_data.pop(chat_id, None)

        if leave_vc:
            session = self._active_ub.pop(chat_id, None)
            pytg    = self._get_instance(session)
            if pytg:
                try:
                    await pytg.leave_call(chat_id)
                    log.info(f"⏹️ Left VC → chat {chat_id}")
                except Exception as e:
                    log.warning(f"⚠️ leave_call error (already left?): {e}")
        else:
            self._active_ub.pop(chat_id, None)

    async def stop_all(self):
        """Shutdown pe saare active VCs band karo."""
        chat_ids = list(self._active_ub.keys())
        for chat_id in chat_ids:
            await self.stop(chat_id)
        log.info("🛑 All VC streams stopped")

    # ──────────────────────────────────────────
    #  APPLY FILTERS — Live restart with new filters
    # ──────────────────────────────────────────

    async def apply_filters_to_all(self) -> int:
        """
        FFmpeg Settings → Save & Apply button.

        Saare active loops ko naye filters ke saath restart karta hai.
        additional_ffmpeg_parameters DB se live read hoti hain —
        sirf play_loop dobara call karna enough hai.

        Returns: kitne streams update hue
        """
        updated = 0
        for chat_id, (file_path, is_video) in list(self._loop_data.items()):
            session = self._active_ub.get(chat_id)
            success = await self.play_loop(chat_id, file_path, session, is_video)
            if success:
                updated += 1

        log.info(f"✅ Filters applied to {updated} active stream(s)")
        return updated

    # ──────────────────────────────────────────
    #  STATUS — Pings panel ke liye
    # ──────────────────────────────────────────

    def status(self) -> dict:
        return {
            "pytgcalls_instances": len(self._instances),
            "active_streams":      len(self._active_ub),
            "loop_active_chats":   list(self._loop_data.keys()),
        }

    # ──────────────────────────────────────────
    #  INTERNAL HELPERS
    # ──────────────────────────────────────────

    def _resolve(self, session: Optional[str]) -> tuple[Optional[PyTgCalls], str]:
        """
        Session diya toh us specific ka instance do.
        Nahi diya toh pehla available instance do.
        Returns (PyTgCalls | None, session_string)
        """
        if not self._instances:
            log.error("❌ No PyTgCalls instances available")
            return None, ""

        if session and session in self._instances:
            return self._instances[session], session

        ses  = next(iter(self._instances))
        pytg = self._instances[ses]
        return pytg, ses

    def _get_instance(self, session: Optional[str]) -> Optional[PyTgCalls]:
        if not session:
            return None
        return self._instances.get(session)


# ──────────────────────────────────────────────
#  SINGLETON
#
#  Baaki sab files isko import karte hain:
#    from VCFIGHTERS.core.call import vc
# ──────────────────────────────────────────────

vc = VCCall()
