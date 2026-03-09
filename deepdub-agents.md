# DeepDub Agents — Implementation Patterns

This document describes the different ways to build voice agents on top of the DeepDub Python client, ranging from simple batch TTS to fully streaming conversational agents.

## Installation

```bash
pip install deepdub
```

Set your API key as an environment variable or pass it directly:

```bash
export DEEPDUB_API_KEY="your-api-key"
```

```python
from deepdub import DeepdubClient
client = DeepdubClient()                              # reads DEEPDUB_API_KEY
client = DeepdubClient(api_key="your-api-key")        # or pass explicitly
client = DeepdubClient(eu=True)                       # EU region (wss.eu.deepdub.ai)
```

---

## 1. Batch TTS Agent (REST)

The simplest pattern. Send complete text, receive complete audio. No WebSocket needed.

**When to use:** Offline processing, pre-rendering, voiceover generation — anywhere latency doesn't matter.

```
User text ──▶ REST tts() ──▶ Complete audio file
```

```python
from deepdub import DeepdubClient

client = DeepdubClient()
audio = client.tts(
    text="Welcome to DeepDub.",
    voice_prompt_id="your-voice-id",
    model="dd-etts-3.0",
    locale="en-US",
    format="mp3",
)
Path("output.mp3").write_bytes(audio)
```

**Latency:** High (seconds). Full text must be synthesized before any audio is returned.

---

## 2. Async TTS Agent (WebSocket, multiplexed)

Send multiple TTS requests over a single WebSocket. Each request gets a `generationId` and returns chunked audio independently. Good for parallel batch work.

**When to use:** Bulk generation where you want concurrency without opening many connections.

```
             ┌─ text-to-speech (gen A) ──▶ audio chunks A
WebSocket ──┤
             └─ text-to-speech (gen B) ──▶ audio chunks B
```

```python
from deepdub import DeepdubClient
from audiosample import AudioSample

client = DeepdubClient()

async with client.async_connect() as conn:
    audio = AudioSample()
    async for chunk in conn.async_tts(
        text="Hello from the async path.",
        voice_prompt_id="your-voice-id",
        model="dd-etts-3.0",
    ):
        audio += AudioSample(chunk)
    audio.write("output.wav")
```

**Latency:** Medium. Audio arrives in chunks but the full text is sent upfront.

---

## 3. Streaming TTS Agent (WebSocket Director)

Text is streamed token-by-token into the TTS director. The director buffers, batches, and dispatches to TTS workers. Audio chunks start arriving before the full text is sent.

**When to use:** Interactive applications where text is produced incrementally — the key building block for voice agents.

```
Text tokens ──stream-text──▶ Director ──▶ TTS workers ──▶ Audio chunks
```

```python
from deepdub import DeepdubClient
from audiosample import AudioSample

client = DeepdubClient()

async with client.async_stream_connect(
    model="dd-etts-3.0",
    locale="en-US",
    voice_prompt_id="your-voice-id",
    sample_rate=16000,
    format="s16le",
) as conn:
    # Stream text in as it becomes available
    for token in ["Hello, ", "how ", "are ", "you ", "today?"]:
        await conn.async_stream_text(token)
    await conn.async_stream_end()

    # Collect audio chunks
    audio = AudioSample(force_read_format="s16le", force_read_sample_rate=16000)
    while True:
        response = await conn.async_stream_recv()
        if response is None:
            continue
        if response.get("data"):
            audio += AudioSample(
                base64.b64decode(response["data"]),
                force_read_format="s16le",
                force_read_sample_rate=16000,
            )
        if response.get("isFinished"):
            break
    audio.write("streamed.wav")
```

**Latency:** Low. Audio generation starts as soon as the director has enough buffered text.

---

## 4. Streaming Voice Agent (STT → LLM → TTS)

The primary use case. A user speaks, speech is transcribed, an LLM generates a response token-by-token, and each token is immediately streamed into DeepDub TTS. The user hears the response while the LLM is still thinking.

```
┌──────────┐      ┌──────────┐      ┌──────────────┐      ┌──────────────┐
│   User   │─mic─▶│   STT    │─text─▶│     LLM      │─tok─▶│  DeepDub TTS │─audio─▶ Speaker
│          │◀─spk─│          │      │  (streaming)  │     │  (streaming)  │
└──────────┘      └──────────┘      └──────────────┘      └──────────────┘
```

### Architecture

Three concurrent async tasks connected by the event loop:

| Task | Responsibility |
|------|----------------|
| **STT listener** | Captures microphone audio, sends to STT provider, yields transcript chunks |
| **LLM streamer** | Takes transcript, calls LLM with streaming, yields response tokens |
| **TTS streamer** | Feeds tokens into `async_stream_text`, reads audio chunks, plays to speaker |

### Core implementation

```python
import asyncio
import base64
from deepdub import DeepdubClient

VOICE_ID = "your-voice-prompt-id"
MODEL = "dd-etts-3.0"
LOCALE = "en-US"
SAMPLE_RATE = 16000
FORMAT = "s16le"


async def llm_stream(prompt: str):
    """Yields text tokens from your LLM of choice."""
    # Example with OpenAI
    from openai import AsyncOpenAI
    oai = AsyncOpenAI()
    stream = await oai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def streaming_voice_agent(user_transcript: str):
    """
    Given a user's spoken input (already transcribed), stream the LLM
    response through DeepDub TTS and yield audio chunks in real time.
    """
    client = DeepdubClient()

    async with client.async_stream_connect(
        model=MODEL,
        locale=LOCALE,
        voice_prompt_id=VOICE_ID,
        sample_rate=SAMPLE_RATE,
        format=FORMAT,
    ) as conn:

        # --- Producer: feed LLM tokens into TTS ---
        async def produce():
            async for token in llm_stream(user_transcript):
                await conn.async_stream_text(token)
            await conn.async_stream_end()

        # --- Consumer: read audio chunks and play them ---
        async def consume():
            while True:
                response = await conn.async_stream_recv()
                if response is None:
                    continue
                if response.get("data"):
                    audio_bytes = base64.b64decode(response["data"])
                    yield audio_bytes  # hand off to audio playback
                if response.get("isFinished"):
                    break

        producer_task = asyncio.create_task(produce())

        async for audio_chunk in consume():
            play_audio(audio_chunk)  # your audio output function

        await producer_task
```

### Interruption handling (barge-in)

When the user starts speaking mid-response, the agent should stop TTS immediately:

```python
async def handle_barge_in(conn, producer_task: asyncio.Task):
    """Call this when STT detects the user is speaking again."""
    # 1. Stop the LLM from producing more tokens
    producer_task.cancel()

    # 2. Cancel the current TTS generation
    await conn.async_stream_cancel()

    # 3. Drain any remaining audio messages (look for isCancelled)
    while True:
        response = await conn.async_stream_recv()
        if response and response.get("isCancelled"):
            break
        if response and response.get("isFinished"):
            break

    # 4. Flush the local audio playback buffer
    flush_playback_buffer()
```

### Mid-stream voice/language switching

For multilingual agents, use inline `<config />` tags in the text stream to switch language or voice without restarting the connection:

```python
async def multilingual_agent(conn):
    await conn.async_stream_text("Let me answer in Spanish. ")
    await conn.async_stream_text('<config locale="es-MX" />')
    await conn.async_stream_text("Hola, ¿cómo puedo ayudarte?")
    await conn.async_stream_end()
```

Or switch the voice entirely:

```python
await conn.async_stream_text("Now a different speaker. ")
await conn.async_stream_text(f'<config voicePromptId="{other_voice_id}" locale="en-US" />')
await conn.async_stream_text("Hi, I'm the other voice.")
```

---

## 5. Full Duplex Conversational Agent

Extends pattern 4 into a continuous conversation loop. The connection stays open across multiple turns using `cancel` between turns and keepalive `ping` during idle periods.

```
┌─────────────────────────────────────────────────────────────┐
│                    Persistent WebSocket                      │
│                                                             │
│  Turn 1: STT → LLM → stream-text → audio → end-stream     │
│  Turn 2: STT → LLM → stream-text → audio → end-stream     │
│  ...                                                        │
│  (ping/pong keepalive between turns)                        │
│  (cancel on barge-in)                                       │
└─────────────────────────────────────────────────────────────┘
```

```python
async def conversation_loop():
    client = DeepdubClient()

    async with client.async_stream_connect(
        model=MODEL, locale=LOCALE, voice_prompt_id=VOICE_ID,
        sample_rate=SAMPLE_RATE, format=FORMAT,
    ) as conn:

        while True:
            # Wait for user to speak
            user_text = await stt_listen()
            if user_text.lower() in ("goodbye", "exit"):
                break

            # Stream LLM response through TTS
            producer = asyncio.create_task(
                feed_llm_to_tts(conn, user_text)
            )
            await play_audio_until_finished(conn)
            await producer

            # Keepalive while waiting for next turn
            await conn.async_stream_ping()


async def feed_llm_to_tts(conn, user_text: str):
    async for token in llm_stream(user_text):
        await conn.async_stream_text(token)
    await conn.async_stream_end()


async def play_audio_until_finished(conn):
    while True:
        response = await conn.async_stream_recv()
        if response is None:
            continue
        if response.get("data"):
            play_audio(base64.b64decode(response["data"]))
        if response.get("isFinished"):
            break
```

---

## Latency Comparison

| Pattern | Time to first audio | Use case |
|---------|---------------------|----------|
| Batch REST | ~2-5s | Offline, pre-rendering |
| Async WebSocket | ~1-3s | Parallel bulk generation |
| Streaming TTS | ~200-500ms | Interactive, known text |
| STT → LLM → Stream | ~500ms-1.5s (STT + LLM TTFT + TTS) | Voice agents |

The streaming voice agent's perceived latency is dominated by:
1. **STT finalization** — time for the STT to commit the transcript
2. **LLM time-to-first-token** — time for the LLM to start responding
3. **TTS director buffering** — the director waits for enough text to form a natural speech segment before dispatching

Items 1 and 2 are outside DeepDub's control. Item 3 is typically 100-300ms once tokens start flowing.

---

## DeepDub Client Methods Reference

### Streaming connection (`async_stream_connect` context)

| Method | Protocol action | Description |
|--------|----------------|-------------|
| `async_stream_text(text)` | `stream-text` | Send text (or partial text) for synthesis |
| `async_stream_end()` | `end-stream` | Signal that no more text is coming for this turn |
| `async_stream_cancel()` | `cancel` | Abort current generation, clear buffers |
| `async_stream_ping()` | `ping` | Keepalive; returns the `pong` response |
| `async_stream_recv()` | — | Receive next JSON message from server |
| `async_stream_recv_audio()` | — | Receive and decode next audio chunk as bytes |
| `async_stream_config(...)` | `stream-config` | Reconfigure session (called automatically by `async_stream_connect`) |

### Server message types

| Field | Meaning |
|-------|---------|
| `action: "status"` | Connection established, includes `connectionId` |
| `action: "pong"` | Response to `ping` |
| `action: "error"` | Session-level error with `message` |
| `generationId` | Audio chunk — includes `index`, `data` (base64), `isFinished` |
| `isCancelled: true` | Generation was cancelled via `cancel` command |
| `error` (with `generationId`) | Per-generation error from a TTS worker |
