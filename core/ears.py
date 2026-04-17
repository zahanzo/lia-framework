"""
ears.py — Audio input module (microphone + transcription)

All heavy dependencies are loaded lazily — only when the selected engine
is actually used. pyaudio is the only mandatory runtime dependency.

Engines:
  whisper  — faster-whisper (local, requires: torch, faster-whisper, pyaudio)
  google   — Google Speech Recognition (online, requires: SpeechRecognition, pyaudio)

Listen modes:
  button   — hold a mouse button to record (default)
  silero   — continuous VAD detection (requires: torch, numpy, pyaudio)
"""

import io
import os
import wave
import core.config as config
from core.i18n import t

# ── State ────────────────────────────────────────────────────────────────────
_whisper_model = None
_whisper_size_loaded: str | None = None
_vad_model     = None
_interrupt_flag = False   # set to True when AI speech should be interrupted


# ==========================================
# LAZY LOADERS
# ==========================================
def _load_whisper():
    """Reload the model if the size in config changes (WebUI panel)."""
    global _whisper_model, _whisper_size_loaded
    size = getattr(config, "WHISPER_MODEL", "small") or "small"
    if _whisper_model is not None and _whisper_size_loaded == size:
        return _whisper_model
    _whisper_model = None
    _whisper_size_loaded = size
    try:
        _patch_torch()
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
        print(t("ears.whisper_loaded", size=size))
    except ImportError:
        print(t("ears.whisper_missing_pkg"))
    except Exception as e:
        print(t("ears.whisper_load_error", e=e))
    return _whisper_model


def _load_vad():
    global _vad_model
    if _vad_model is not None:
        return _vad_model
    try:
        _patch_torch()
        import torch
        _vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
            verbose=False
        )
        print(t("ears.vad_loaded"))
    except ImportError as e:
        print(t("ears.vad_torch_error", e=e))
    except Exception as e:
        print(t("ears.vad_load_error", e=e))
    return _vad_model


def _patch_torch():
    """Patch torch.load to avoid weights_only deprecation warnings from faster-whisper."""
    try:
        import torch
        if not getattr(torch, "_load_patched", False):
            _orig = torch.load
            def _patched(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return _orig(*args, **kwargs)
            torch.load = _patched
            torch._load_patched = True
    except ImportError:
        pass


def _get_pyaudio():
    """Import pyaudio lazily with a clear error message."""
    try:
        import pyaudio
        return pyaudio
    except ImportError:
        print(t("ears.pyaudio_missing"))
        return None


# ==========================================
# TRANSCRIPTION
# ==========================================
def _transcribe(frames: list, fmt, channels: int, rate: int, sample_width: int) -> str:
    """Convert recorded audio frames to text using the configured STT engine."""
    # Build WAV buffer
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(b"".join(frames))
    wav_buf.seek(0)

    engine = getattr(config, "STT_ENGINE", "whisper")
    lang = config.config_data.get("ui_language", "en")

    # ── Whisper ───────────────────────────────────────────────────────
    if engine == "whisper":
        model = _load_whisper()
        if model:
            try:
                tmp = "_tmp_audio.wav"
                with open(tmp, "wb") as f:
                    f.write(wav_buf.getvalue())

                segments, _ = model.transcribe(
                    tmp,
                    beam_size=5,
                    vad_filter=True,
                    condition_on_previous_text=False,
                    language=lang
                )
                text = "".join(s.text for s in segments).strip()

                if os.path.exists(tmp):
                    os.remove(tmp)

                if text:
                    print(t("ears.whisper_heard", text=text))
                    return text
                print(t("ears.whisper_empty"))
                return ""
            except Exception as e:
                print(t("ears.whisper_error", e=e))
                return ""

    # ── Google STT (only if engine = google in dashboard) ────────────
    if engine == "google":
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            wav_buf.seek(0)
            with sr.AudioFile(wav_buf) as source:
                audio_data = recognizer.record(source)
            print(t("ears.google_stt_working"))
            text = recognizer.recognize_google(audio_data)
            print(t("ears.google_stt_heard", text=text))
            return text.lower()
        except ImportError:
            print(t("ears.google_stt_missing"))
        except Exception:
            print(t("ears.google_stt_fail"))

    return ""


# ==========================================
# MODE 1: BUTTON (hold to record)
# ==========================================
def listen_button(message: str, button: str) -> str:
    """Record while the given mouse button is held, then transcribe."""
    import mouse
    import pygame

    pyaudio = _get_pyaudio()
    if not pyaudio:
        return ""

    FORMAT   = pyaudio.paInt16
    CHANNELS = 1
    RATE     = 16000
    CHUNK    = 1024

    # Stop AI speech if playing
    global _interrupt_flag
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
        _interrupt_flag = True

    print(message)
    audio  = pyaudio.PyAudio()
    stream = None
    frames = []

    try:
        stream = audio.open(
            format=FORMAT, channels=CHANNELS, rate=RATE,
            input=True, frames_per_buffer=CHUNK
        )
        while mouse.is_pressed(button):
            frames.append(stream.read(CHUNK))

        # Capture 300ms tail after release
        for _ in range(int(RATE / CHUNK * 0.3)):
            try:
                frames.append(stream.read(CHUNK))
            except Exception:
                break

        print(t("ears.button_released"))
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()

    return _transcribe(frames, FORMAT, CHANNELS, RATE,
                       pyaudio.PyAudio().get_sample_size(FORMAT))

# Backward compatibility alias
ouvir_microfone = listen_button


# ==========================================
# MODE 2: CONTINUOUS VAD (Silero)
# ==========================================
def listen_continuous_vad() -> str:
    """
    Continuously listen for voice using Silero VAD.
    Returns transcribed text when a sentence ends.
    Also handles pending web/watchdog messages.
    """
    import pygame

    pyaudio = _get_pyaudio()
    if not pyaudio:
        return ""

    vad = _load_vad()
    if not vad:
        print(t("ears.vad_fallback"))
        return ""

    try:
        import torch
        import numpy as np
    except ImportError:
        print(t("ears.vad_deps_missing"))
        return ""

    FORMAT   = pyaudio.paInt16
    CHANNELS = 1
    RATE     = 16000
    CHUNK    = 512

    audio         = pyaudio.PyAudio()
    stream        = None
    recorded      = []
    recording     = False
    silence_count = 0
    SILENCE_LIMIT = int(RATE / CHUNK * 1.5)

    global _interrupt_flag

    # Avoid circular import: mouth doesn't import ears
    from core.mouth import is_speaking as _ai_is_speaking

    import time

    _tts_was_active = False
    _post_tts_cooldown_until = 0.0
    _vad_post_tts_cooldown_sec = 0.55

    print(t("ears.vad_open"))

    try:
        stream = audio.open(
            format=FORMAT, channels=CHANNELS, rate=RATE,
            input=True, frames_per_buffer=CHUNK
        )

        while True:
            config.mic_state = "listening"

            # Check for pending web / watchdog message
            if config.pending_web_input:
                content = config.pending_web_input
                config.pending_web_input = None
                print(t("turn.web_received"))
                config.mic_state = "processing"
                return content

            speaking_now = _ai_is_speaking()
            if speaking_now:
                _tts_was_active = True
            elif _tts_was_active:
                _tts_was_active = False
                _post_tts_cooldown_until = time.monotonic() + _vad_post_tts_cooldown_sec

            data     = stream.read(CHUNK, exception_on_overflow=False)
            audio_np = (
                __import__("numpy")
                .frombuffer(data, dtype=__import__("numpy").int16)
                .astype(__import__("numpy").float32) / 32768.0
            )

            with torch.no_grad():
                confidence = vad(torch.from_numpy(audio_np), RATE).item()

            if confidence > 0.5:
                if speaking_now:
                    silence_count = 0
                    continue
                if (not recording
                        and time.monotonic() < _post_tts_cooldown_until):
                    silence_count = 0
                    continue
                if not recording:
                    print(t("ears.vad_detected"))
                    recording = True
                    config.mic_state = "recording"
                    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                        _interrupt_flag = True
                silence_count = 0
                recorded.append(data)
            else:
                if recording:
                    recorded.append(data)
                    silence_count += 1
                    if silence_count > SILENCE_LIMIT:
                        config.mic_state = "processing"
                        break

    except Exception as e:
        print(t("ears.vad_capture_error", e=e))
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()

    if recorded:
        return _transcribe(recorded, FORMAT, CHANNELS, RATE,
                           pyaudio.PyAudio().get_sample_size(FORMAT))
    return ""

ouvir_microfone = listen_button
ouvir_continuo_vad = listen_continuous_vad