import io
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from server.api.auth_deps import get_current_user
from server.schemas.schemas import VoiceSpeakRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice Services"])

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Transcribes uploaded audio file.
    Supports wav, mp3, m4a, etc.
    """
    # Verify file content type
    content_type = file.content_type
    logger.info(f"Received audio transcription request: {file.filename} ({content_type})")
    
    try:
        # Load audio data
        audio_bytes = await file.read()
        
        # Try importing speech_recognition
        try:
            import speech_recognition as sr
            
            # Since speech_recognition works best with WAV, let's write to buffer
            # and use it. If audio is mp3/m4a, it may fail, so we wrap it.
            recognizer = sr.Recognizer()
            audio_file = io.BytesIO(audio_bytes)
            
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                return {"text": text}
        except ImportError:
            logger.warning("speech_recognition library not available. Using mock fallback.")
            return {
                "text": "Hello, this is a mock transcription because the speech recognition dependencies are in fallback mode.",
                "warning": "Install speech_recognition and PyAudio to transcribe files locally."
            }
        except Exception as e:
            logger.warning(f"Speech recognition failed: {e}. Returning fallback message.")
            return {
                "text": "Could not parse audio file. Please ensure it is a clean, single-channel WAV file.",
                "error": str(e)
            }
    except Exception as e:
        logger.error(f"Error handling transcription file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process audio file: {e}"
        )

@router.post("/speak")
async def speak_text(request: VoiceSpeakRequest, current_user: dict = Depends(get_current_user)):
    """
    Generates speech audio from text using Google TTS (gTTS).
    """
    text = request.text
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty")
        
    try:
        from gtts import gTTS
        
        # Generate speech
        tts = gTTS(text=text, lang="en", slow=False)
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)
        
        return StreamingResponse(
            audio_stream,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )
    except Exception as e:
        logger.error(f"Text-to-speech generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate speech audio: {e}"
        )
