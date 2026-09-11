import base64
import io
import os
import tempfile
import wave

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
    Convert microphone audio into text.

    Primary:
        Gemini 3.5 Transcribe

    Fallback:
        The normal ORCA Gemini model with audio understanding.
    """

    if not audio_bytes:
        raise ValueError("Audio data is empty.")

    suffix = ".webm"

    if "wav" in mime_type:
        suffix = ".wav"
    elif "mp3" in mime_type or "mpeg" in mime_type:
        suffix = ".mp3"
    elif "ogg" in mime_type:
        suffix = ".ogg"
    elif "m4a" in mime_type or "mp4" in mime_type:
        suffix = ".m4a"

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp:
            temp.write(audio_bytes)
            temp_path = temp.name

        audio_file = client.files.upload(
            file=temp_path
        )

        # -------------------------------------------------
        # PRIMARY: Gemini 3.5 Transcribe
        # -------------------------------------------------
        try:
            print(
                "ORCA Voice: trying Gemini 3.5 Transcribe..."
            )

            response = client.models.generate_content(
                model="gemini-3.5-transcribe",
                contents=[audio_file],
                config=types.GenerateContentConfig(
                    audio_transcription_config=(
                        types.AudioTranscriptionConfig(
                            mode="VERBATIM",
                            custom_vocabulary=[
                                "ORCA",
                                "PFZ",
                                "fishing zone",
                                "fishing zones",
                                "sea surface temperature",
                                "SST",
                                "chlorophyll",
                                "latitude",
                                "longitude",
                                "Indian Ocean",
                                "Arabian Sea",
                                "Bay of Bengal",
                                "cyclone",
                                "storm",
                                "wind",
                                "wave",
                                "weather",
                                "nautical",
                                "navigation",
                            ],
                        )
                    )
                ),
            )

            text = (response.text or "").strip()

            if text:
                print(
                    "ORCA Voice: Gemini Transcribe succeeded."
                )
                return text

        except Exception as transcribe_error:
            print(
                "ORCA Voice: Gemini Transcribe unavailable:"
            )
            print(transcribe_error)

        # -------------------------------------------------
        # FALLBACK: Existing ORCA Gemini model
        # -------------------------------------------------

        fallback_model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite",
        )

        print(
            f"ORCA Voice: using fallback model "
            f"{fallback_model}..."
        )

        fallback_prompt = """
You are a speech transcription system for the ORCA
marine intelligence application.

Transcribe the user's speech exactly as spoken.

Important requirements:

1. Return ONLY the transcription.
2. Do not explain anything.
3. Do not answer the user's question.
4. Preserve the user's language.
5. Preserve Hinglish/code-switching.
6. Do not translate Hindi into English.
7. Correctly recognize marine terminology such as:
   PFZ, fishing zone, SST, chlorophyll,
   latitude, longitude, Indian Ocean,
   Arabian Sea, Bay of Bengal,
   cyclone, storm, wind, waves,
   weather and navigation.

If the user says a Hindi/English mixed sentence,
keep it mixed.

Example:
"Mujhe aaj ke fishing zones batao"

should remain approximately:
"Mujhe aaj ke fishing zones batao"
"""

        fallback_response = client.models.generate_content(
            model=fallback_model,
            contents=[
                fallback_prompt,
                audio_file,
            ],
        )

        text = (fallback_response.text or "").strip()

        if not text:
            raise ValueError(
                "Neither Gemini transcription model "
                "nor fallback Gemini model returned text."
            )

        print(
            "ORCA Voice: fallback transcription succeeded."
        )

        return text

    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            
            
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