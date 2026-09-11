import os
import tempfile

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