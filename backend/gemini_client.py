import base64
import io
import os
import tempfile
import wave
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)


def ask_gemini(prompt: str) -> str:
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL"),
        contents=prompt,
    )

    return response.text


def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
) -> str:
    """
    Transcribe short browser-recorded audio directly using Gemini.

    Uses inline audio bytes instead of the Gemini Files API.
    This avoids Files API PROCESSING/ACTIVE failures.
    """

    if not audio_bytes:
        raise ValueError("No audio data received.")

    print(
        f"ORCA Voice: received {len(audio_bytes)} bytes "
        f"with MIME type {mime_type}"
    )

    # Gemini expects a proper audio MIME type.
    # Browser MediaRecorder may send parameters such as:
    # audio/webm;codecs=opus
    clean_mime_type = mime_type.split(";")[0].strip().lower()

    # Normalize common browser MIME types.
    if clean_mime_type == "audio/ogg":
        clean_mime_type = "audio/ogg"
    elif clean_mime_type == "audio/webm":
        clean_mime_type = "audio/webm"
    elif clean_mime_type == "audio/wav":
        clean_mime_type = "audio/wav"
    elif clean_mime_type == "audio/mp4":
        clean_mime_type = "audio/mp4"
    elif clean_mime_type == "audio/mpeg":
        clean_mime_type = "audio/mpeg"
    elif clean_mime_type == "audio/mp3":
        clean_mime_type = "audio/mp3"
    else:
        print(
            f"ORCA Voice: unknown MIME type {clean_mime_type}, "
            "falling back to audio/webm"
        )
        clean_mime_type = "audio/webm"

    try:
        # Send the audio directly to Gemini.
        audio_part = types.Part.from_bytes(
            data=audio_bytes,
            mime_type=clean_mime_type,
        )

        response = client.models.generate_content(
            model="gemini-3.5-transcribe",
            contents=[
                audio_part,
                """
                Transcribe the spoken audio exactly.

                Return ONLY the transcription text.
                Do not explain the transcription.
                Do not add quotation marks.
                Preserve the language spoken by the user.
                """,
            ],
            config=types.GenerateContentConfig(
                audio_transcription_config=types.AudioTranscriptionConfig(
                    mode="VERBATIM",
                    custom_vocabulary=[
                        "ORCA",
                        "PFZ",
                        "fishing zone",
                        "fishing potential",
                        "chlorophyll",
                        "sea surface temperature",
                        "SST",
                        "cyclone",
                        "wave height",
                        "wind speed",
                        "ocean current",
                        "MOSDAC",
                        "INCOIS",
                        "Copernicus",
                        "vessel",
                        "route",
                        "safety",
                    ],
                )
            ),
        )

        # Gemini 3.5 Transcribe may return the transcript
        # inside an audio_transcription response part
        # instead of response.text.
        transcript = ""

        parts = getattr(response, "parts", []) or []

        for part in parts:
            # Normal text response
            text = getattr(part, "text", None)

            if text:
                transcript += str(text).strip()

            # Gemini transcription response
            audio_transcription = getattr(
                part,
                "audio_transcription",
                None,
            )

            if audio_transcription:
                transcription_text = getattr(
                    audio_transcription,
                    "text",
                    None,
                )

                if transcription_text:
                    transcript += str(
                        transcription_text
                    ).strip()

        transcript = transcript.strip()

        # Fallback for SDK versions where response.text
        # exposes the transcription normally.
        if not transcript:
            transcript = (
                getattr(response, "text", "") or ""
            ).strip()

        if not transcript:
            print(
                "ORCA Voice: Gemini response contained "
                "no transcript."
            )

            # Useful debugging information
            print(
                "ORCA Voice: response parts =",
                getattr(response, "parts", None),
            )

            raise RuntimeError(
                "Gemini returned an empty transcription."
            )

        print(
            f"ORCA Voice: transcription = {transcript}"
        )

        return transcript

    except Exception as e:
        print(
            f"ORCA Gemini transcription error: "
            f"{type(e).__name__}: {e}"
        )
        raise
            
            
def synthesize_speech(text: str) -> bytes:
    """
    Convert an ORCA assistant response into speech.

    Uses Gemini 3.1 Flash TTS Preview and returns
    a WAV audio file as bytes.
    """

    if not text or not text.strip():
        raise ValueError("Text for speech is empty.")

    speech_prompt = f"""
You are the voice of ORCA, a marine intelligence assistant.

Read the following assistant response aloud naturally.

Requirements:
- Speak clearly and naturally.
- Preserve Hindi-English code-switching / Hinglish.
- Do not translate Hindi into English.
- Do not say markdown symbols aloud.
- Do not say formatting instructions aloud.
- Maintain a calm, professional and helpful tone.
- Use natural pauses between different pieces of information.
- Read numbers, coordinates, temperatures and measurements clearly.

The text to speak begins below:

{text}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-tts-preview",
        contents=speech_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore",
                    )
                )
            ),
        ),
    )

    try:
        audio_data = (
            response
            .candidates[0]
            .content
            .parts[0]
            .inline_data
            .data
        )
    except (AttributeError, IndexError, TypeError) as exc:
        raise ValueError(
            "Gemini TTS did not return audio data."
        ) from exc

    if not audio_data:
        raise ValueError(
            "Gemini TTS returned empty audio."
        )

    if isinstance(audio_data, str):
        audio_data = base64.b64decode(audio_data)

    # Gemini returns PCM audio.
    # Wrap it in a WAV container so the browser can play it.
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(audio_data)
        
    wav_bytes = wav_buffer.getvalue()

    print("ORCA TTS WAV size:", len(wav_bytes))
    print("ORCA TTS WAV header:", wav_bytes[:12])

    return wav_bytes

    return wav_buffer.getvalue()