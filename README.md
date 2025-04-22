# DeepDub

A Python client for interacting with the DeepDub API, which provides text-to-speech capabilities with voice cloning features.

## Installation

```bash
pip install deepdub
```

## Features

- Interact with DeepDub's text-to-speech (TTS) API
- Add and manage voice profiles
- Generate speech from text with specified voices
- Command-line interface for easy usage

## Requirements

- Python 3.11+
- API key from DeepDub

## Usage

### Python API Reference

#### Initialization

```python
from deepdub import DeepdubClient

# Initialize with API key directly
client = DeepdubClient(api_key="your-api-key")

# Or use environment variable
# export DEEPDUB_API_KEY=your-api-key
client = DeepdubClient()
```

#### List Voices

```python
# Get all available voices
voices = client.list_voices()
```

Returns a list of voice dictionaries.

#### Add Voice

```python
# Add a new voice from audio file
response = client.add_voice(
    data=Path("path/to/audio.mp3"),  # Path object, bytes, or base64 string
    name="Voice Name",
    gender="male",  # "male" or "female"
    locale="en-US",
    publish=False,  # Default: False
    speaking_style="Neutral",  # Default: "Neutral"
    age=0  # Default: 0
)
```

Returns the server response with voice information.

#### Text-to-Speech

```python
# Generate speech from text
audio_data = client.tts(
    text="Text to be converted to speech",
    voice_prompt_id="your-voice-id",
    model="dd-etts-2.5",  # Default: "dd-etts-2.5"
    locale="en-US"  # Default: "en-US"
)

# Save the audio data
with open("output.mp3", "wb") as f:
    f.write(audio_data)
```

Returns binary audio data.

#### Retroactive Text-to-Speech

```python
# Get URL for generated audio
response = client.tts_retro(
    text="Text to be converted to speech",
    voice_prompt_id="your-voice-id",
    model="dd-etts-2.5",  # Default: "dd-etts-2.5"
    locale="en-US"  # Default: "en-US"
)

# Access the URL
audio_url = response["url"]
```

Returns a dictionary containing the URL to the generated audio.

### Command Line Interface

```bash
# List available voices
deepdub list-voices

# Add a new voice
deepdub add-voice --file path/to/audio.mp3 --name "Voice Name" --gender male --locale en-US

# Generate text-to-speech
deepdub tts --text "Hello, world!" --voice-prompt-id your-voice-id
```

### Python API

```python
from deepdub import DeepdubClient

# Initialize with your API key (or set DEEPDUB_API_KEY environment variable)
client = DeepdubClient(api_key="your-api-key")

# List available voices
voices = client.list_voices()
print(voices)

# Generate speech from text
response = client.tts(
    text="Hello, this is a test",
    voice_prompt_id="your-voice-id",
    locale="en-US"
)

# Save the audio output
with open("output.mp3", "wb") as f:
    f.write(response)
```

## Authentication

Set your API key either:
- As an environment variable: `DEEPDUB_API_KEY=your-key`
- When initializing the client: `DeepdubClient(api_key="your-key")`
- Using the `--api-key` flag with CLI commands

## License

[License information]
