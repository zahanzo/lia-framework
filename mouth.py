"""
mouth.py — Voice synthesis engines

Supported engines: ElevenLabs | Edge-TTS | Kokoro TTS | Piper TTS

Install optional engines:
    pip install kokoro soundfile       ← Kokoro (ElevenLabs-like quality, fast)
    pip install piper-tts              ← Piper  (native language TTS, real-time)

Download Piper model (example for pt-BR):
    curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx
    curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json
"""

import os
import io
import asyncio
import pygame
import config
from i18n import t

# ==========================================
# BASE AUDIO PLAYBACK
# ==========================================
def _play_bytes(audio_bytes: bytes, fmt: str = "mp3"):
    """Play audio bytes via pygame without writing to disk."""
    try:
        audio_io = io.BytesIO(audio_bytes)
        pygame.mixer.init(frequency=22050 if fmt == "wav" else 44100)
        pygame.mixer.music.load(audio_io)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    finally:
        try:
            pygame.mixer.quit()
        except Exception:
            pass


def _play_numpy(array, sample_rate: int = 24000):
    """Play a numpy audio array (used by Kokoro)."""
    try:
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, array, sample_rate, format="WAV")
        buf.seek(0)
        _play_bytes(buf.read(), fmt="wav")
    except Exception as e:
        print(t("voice.error", e=e))


# ==========================================
# ENGINE 1: ELEVENLABS (lazy init)
# ==========================================
_elevenlabs_client = None
_elevenlabs_key_cache = None
ELEVENLABS_VOICE_ID = "CcElPA8NBrawbunFs7rh"  # override in DB config if needed


def _get_elevenlabs_client():
    global _elevenlabs_client, _elevenlabs_key_cache
    key = getattr(config, "ELEVENLABS_API_KEY", "")
    if not key:
        return None
    if _elevenlabs_client is None or key != _elevenlabs_key_cache:
        try:
            from elevenlabs.client import ElevenLabs
            _elevenlabs_client = ElevenLabs(api_key=key)
            _elevenlabs_key_cache = key
        except Exception as e:
            print(t("voice.elevenlabs_error", e=e))
            return None
    return _elevenlabs_client


def _speak_elevenlabs(text: str):
    client = _get_elevenlabs_client()
    if not client:
        print(t("voice.elevenlabs_no_client"))
        return
    try:
        gen = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2"
        )
        audio = b"".join(c for c in gen if c)
        _play_bytes(audio)
    except Exception as e:
        print(t("voice.elevenlabs_error", e=e))


# ==========================================
# ENGINE 2: EDGE-TTS (no temp file)
# ==========================================
async def _speak_edge(text: str):
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, config.VOICE)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        if audio:
            await asyncio.to_thread(_play_bytes, audio)
    except ImportError:
        print("❌ [Edge-TTS] Not installed. Run: pip install edge-tts")
    except Exception as e:
        print(t("voice.edge_error", e=e))


# ==========================================
# ENGINE 3: KOKORO TTS (local, high quality)
# ==========================================
_kokoro_pipeline = None
KOKORO_DEFAULT_VOICE = "af_heart"   # af_heart | af_bella | af_sarah | af_nicole


def _get_kokoro():
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        try:
            from kokoro import KPipeline
            lang = getattr(config, "KOKORO_LANG", "a")  # "a" = English, "p" = Portuguese
            _kokoro_pipeline = KPipeline(lang_code=lang)
            print(t("voice.kokoro_loaded"))
        except ImportError:
            print(t("voice.kokoro_not_installed"))
            return None
        except Exception as e:
            print(t("voice.kokoro_load_error", e=e))
            return None
    return _kokoro_pipeline


def _speak_kokoro(text: str):
    pipeline = _get_kokoro()
    if not pipeline:
        return
    try:
        voice = getattr(config, "KOKORO_VOICE", KOKORO_DEFAULT_VOICE)
        for _, _, audio in pipeline(text, voice=voice, speed=1.0):
            if audio is not None:
                _play_numpy(audio, sample_rate=24000)
    except Exception as e:
        print(t("voice.kokoro_error", e=e))


# ==========================================
# ENGINE 4: PIPER TTS (local, language-native)
# ==========================================
_piper_voice = None
PIPER_DEFAULT_MODEL = "en_US-lessac-medium.onnx"  # download from huggingface.co/rhasspy/piper-voices


def _get_piper():
    global _piper_voice
    if _piper_voice is None:
        try:
            from piper.voice import PiperVoice
            model_file = getattr(config, "PIPER_MODEL", PIPER_DEFAULT_MODEL)
            if not os.path.isabs(model_file):
                model_file = os.path.join(config.BASE_DIR, model_file)
            if not os.path.exists(model_file):
                print(t("voice.piper_not_found", path=model_file))
                return None
            _piper_voice = PiperVoice.load(model_file)
            print(t("voice.piper_loaded", name=os.path.basename(model_file)))
        except ImportError:
            print(t("voice.piper_not_installed"))
            return None
        except Exception as e:
            print(t("voice.piper_error", e=e))
            return None
    return _piper_voice


def _speak_piper(text: str):
    voice = _get_piper()
    if not voice:
        return
    try:
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            voice.synthesize(text, wav)
        buf.seek(0)
        _play_bytes(buf.read(), fmt="wav")
    except Exception as e:
        print(t("voice.piper_error", e=e))


# ==========================================
# ASYNC VOICE QUEUE
# ==========================================
_voice_queue: asyncio.Queue = asyncio.Queue()
_consumer_started = False
_is_speaking = False


def is_speaking() -> bool:
    """True if audio is currently playing or queued."""
    return _is_speaking or not _voice_queue.empty()

esta_falando = is_speaking


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for progressive queuing."""
    import re
    parts = re.split(r'(?<=[.!?…])\s+', text.strip())
    result, buffer = [], ""
    for part in parts:
        buffer = (buffer + " " + part).strip()
        if len(buffer) >= 30:
            result.append(buffer)
            buffer = ""
    if buffer:
        result.append(buffer)
    return result if result else [text]


async def speak(text: str):
    """Enqueue text for speech. Non-blocking."""
    print(t("turn.ai", text=text))
    for sentence in _split_into_sentences(text):
        await _voice_queue.put(sentence)

gerar_voz = speak


async def _voice_consumer():
    """Background task — consumes the queue and plays audio sequentially."""
    global _is_speaking

    # Import lipsync lazily — only starts if enabled in dashboard settings
    _lipsync_available = False
    try:
        if getattr(config, "LIPSYNC_ENABLED", False):
            import lipsync as _lipsync
            _lipsync.start()
            _lipsync_available = True
            print("[Voice] LipSync started.")
        else:
            print("[Voice] LipSync disabled (enable in dashboard → System).")
    except ImportError:
        pass

    while True:
        text = await _voice_queue.get()
        _is_speaking = True
        if _lipsync_available:
            _lipsync.set_speaking(True)
        try:
            engine = getattr(config, "CURRENT_VOICE_MODE", "edge").lower()
            if engine in ("elevenlabs", "eleven"):
                await asyncio.to_thread(_speak_elevenlabs, text)
            elif engine == "kokoro":
                await asyncio.to_thread(_speak_kokoro, text)
            elif engine == "piper":
                await asyncio.to_thread(_speak_piper, text)
            else:
                await _speak_edge(text)
        except Exception as e:
            print(t("voice.error", e=e))
        finally:
            _voice_queue.task_done()
            if _voice_queue.empty():
                _is_speaking = False
                if _lipsync_available:
                    _lipsync.set_speaking(False)


def start_voice_consumer():
    """Start the queue consumer. Call ONCE at boot."""
    global _consumer_started
    if not _consumer_started:
        asyncio.ensure_future(_voice_consumer())
        _consumer_started = True
        print(t("voice.consumer_started"))

iniciar_consumidor_voz = start_voice_consumer


async def clear_queue():
    """Stop current playback and flush the queue."""
    global _is_speaking
    _is_speaking = False
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass
    while not _voice_queue.empty():
        try:
            _voice_queue.get_nowait()
            _voice_queue.task_done()
        except asyncio.QueueEmpty:
            break

limpar_fila = clear_queue