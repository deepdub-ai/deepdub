"""
Example demonstrating the gender_classify API.

This example shows how to classify the gender of a speaker from an audio sample.
The API automatically trims audio to the first 1 second.
"""
import asyncio
import logging
from pathlib import Path
from deepdub import DeepdubClient
from audiosample import AudioSample

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

client = DeepdubClient()

# Voice prompt for generating test audio
VOICE_PROMPT_ID = "5d3dc622-69bd-4c00-9513-05df47dbdea6_authoritative"


async def classify_from_file(audio_path: Path):
    """Classify gender from an audio file."""
    logger.info("Classifying gender from file: %s", audio_path)
    result = await client.gender_classify(audio_path)
    logger.info("  Predicted gender: %s", result['predicted_gender'])
    logger.info("  Confidence: %s", result['confidence'])
    return result


async def classify_from_audio(audio: AudioSample):
    """Classify gender from an AudioSample."""
    logger.info("Classifying gender from AudioSample...")
    # Use as_wav_data() to get properly formatted audio bytes
    result = await client.gender_classify(audio.as_wav_data())
    logger.info("  Predicted gender: %s", result['predicted_gender'])
    logger.info("  Confidence: %s", result['confidence'])
    return result


async def main():
    # Example 1: Generate audio and classify it
    logger.info("=" * 50)
    logger.info("Example 1: Generate TTS and classify gender")
    logger.info("=" * 50)
    
    # First generate some audio using TTS
    audio = AudioSample()
    async with client.async_connect() as connection:
        async for chunk in connection.async_tts(
            text="Hello, this is a test of the gender classification API.",
            voice_prompt_id=VOICE_PROMPT_ID,
            locale="en-US"
        ):
            audio += AudioSample(chunk)
    
    # Save for later use
    audio.write("test_audio.wav")
    logger.info("Generated test audio: test_audio.wav\n")
    
    # Classify from AudioSample
    await classify_from_audio(audio)
    
    # Example 2: Classify from file
    logger.info("\n" + "=" * 50)
    logger.info("Example 2: Classify from file path")
    logger.info("=" * 50)
    await classify_from_file(Path("test_audio.wav"))
    
    # Cleanup
    Path("test_audio.wav").unlink(missing_ok=True)
    logger.info("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
