"""
Example demonstrating the gender_classify API.

This example shows how to classify the gender of a speaker from an audio sample.
The API automatically trims audio to the first 1 second.
"""
import asyncio
from pathlib import Path
from deepdub import DeepdubClient
from audiosample import AudioSample

client = DeepdubClient()

# Voice prompt for generating test audio
VOICE_PROMPT_ID = "5d3dc622-69bd-4c00-9513-05df47dbdea6_authoritative"


async def classify_from_file(audio_path: Path):
    """Classify gender from an audio file."""
    print(f"Classifying gender from file: {audio_path}")
    result = await client.gender_classify(audio_path)
    print(f"  Predicted gender: {result['predicted_gender']}")
    print(f"  Confidence: {result['confidence']}")
    return result


async def classify_from_audio(audio: AudioSample):
    """Classify gender from an AudioSample."""
    print("Classifying gender from AudioSample...")
    # Use as_wav_data() to get properly formatted audio bytes
    result = await client.gender_classify(audio.as_wav_data())
    print(f"  Predicted gender: {result['predicted_gender']}")
    print(f"  Confidence: {result['confidence']}")
    return result


async def main():
    # Example 1: Generate audio and classify it
    print("=" * 50)
    print("Example 1: Generate TTS and classify gender")
    print("=" * 50)
    
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
    print(f"Generated test audio: test_audio.wav\n")
    
    # Classify from AudioSample
    await classify_from_audio(audio)
    
    # Example 2: Classify from file
    print("\n" + "=" * 50)
    print("Example 2: Classify from file path")
    print("=" * 50)
    await classify_from_file(Path("test_audio.wav"))
    
    # Cleanup
    Path("test_audio.wav").unlink(missing_ok=True)
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
