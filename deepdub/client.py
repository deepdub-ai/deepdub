import asyncio
import base64
import json
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from audiosample import AudioSample

import requests
import websockets

MODEL_LIST = ["dd-etts-3.0", "dd-etts-2.5", "dd-etts-1.1"]

class DeepdubClient:
    """
    Client for interacting with the DeepDub API.
    """

    def data_input_preprocess(self, data: Union[bytes, str, Path]) -> str:
        if isinstance(data, Path):
            filename = data.name
            with open(data, "rb") as f:
                data = f.read()
                data = base64.b64encode(data).decode("utf-8")
        elif isinstance(data, bytes):
            data = base64.b64encode(data).decode("utf-8")
            filename = str(uuid4())
        elif isinstance(data, str):
            try:
                test_data = base64.b64decode(data)
                filename = str(uuid4())
            except Exception as e:
                raise ValueError("string data must be base64 encoded")
        else:
            raise ValueError("Invalid data type")

        return data, filename

    def __init__(self, base_url: Optional[str] = None, 
            base_websocket_url: Optional[str] = None, 
            base_websocket_streaming_url: Optional[str] = None, 
            api_key: Optional[str] = None,
            eu: Optional[bool] = None):
        """
        Initialize the DeepDub API client.
        
        Args:
            base_url: Base URL for the DeepDub REST API
            base_websocket_url: Base WebSocket URL
            base_websocket_streaming_url: Base WebSocket streaming URL
            api_key: API key for authentication (if required)
            eu: Use EU region endpoints. If None, checks DD_EU env var.
        """
        if eu is None:
            eu = os.environ.get("DD_EU", "0") == "1"
        region = ".eu" if eu else ""

        self.base_url = base_url or os.environ.get("DEEPDUB_BASE_URL") or f"https://restapi{region}.deepdub.ai/api/v1"
        self.base_websocket_url = base_websocket_url or os.environ.get("DEEPDUB_BASE_WEBSOCKET_URL") or f"wss://wsapi{region}.deepdub.ai/open"
        self.base_websocket_streaming_url = base_websocket_streaming_url or os.environ.get("DEEPDUB_BASE_WEBSOCKET_STREAMING_URL") or f"wss://wss{region}.deepdub.ai/ws"
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv("DEEPDUB_API_KEY", None)
        if not self.api_key:
            raise ValueError("No API key provided, supply it as an argument or set the DEEPDUB_API_KEY environment variable")
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        self.dd_wav_header_len = 0x44

        self.websocket = None

    def proxy_request(self, method: str, url: str, *args, **kwargs) -> Any:
        url = f"{self.base_url}{url}"
        if "headers" in kwargs:
            kwargs["headers"] = {**self.headers, **kwargs["headers"]}
        else:
            kwargs["headers"] = self.headers
        response = requests.__getattribute__(method)(url, *args, **kwargs)
        response.raise_for_status()
        if response.headers.get('content-type', '').startswith('application/json'):
            return response.json()
        else:
            return response.content



    def __getattr__(self, name: str) -> Any:
        """
        Get an attribute from the client.
        """
        if ["get", "post", "put", "delete"].__contains__(name):
            return partial(self.proxy_request, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    # Asset endpoints
    def list_voices(self) -> List[Dict]:
        """
        Adds a voice to the DeepDub API.
        Parameters:
            data: Union[bytes, str, Path] - The data of the voice (bytes, base64 encoded string, or path to a file)
            name: str - The name of the voice
            gender: str - The gender of the voice
            locale: str - The locale of the voice
            publish: bool - Whether to publish the voice
            speaking_style: str - The speaking style of the voice
            age: int - The age of the voice
        Returns:
            List of voice dictionaries
        """
        return self.get("/voice")
    
    def add_voice(self, data: Union[bytes, str, Path], name: str, gender: str, locale: str, publish: bool = False, speaking_style: str = "Neutral", age: int = 0) -> str:
        """
        Get a voice by ID.
        """
        data, filename = self.data_input_preprocess(data)
        gender = gender.lower()
        assert gender in ["male", "female"]
        voice = {
            "name": name,
            "gender": gender,
            "age": age,
            "locale": locale,
            "publish": publish,
            "speaking_style": speaking_style,
            "speaker_id": str(uuid4()),
            "title": f"{name}-{gender}-{age}-{locale}-{speaking_style}",
            "data": data,
            "filename": filename
        }
        return self.post(f"/voice", json=voice)


    def tts(self, text: str, 
            voice_reference: Optional[Union[bytes, str, Path]] = None,
            voice_prompt_id: Optional[str] = None, 
            model: str = "dd-etts-2.5", 
            locale: str = "en-US",
            temperature: Optional[float] = None,
            variance: Optional[float] = None,
            duration: Optional[float] = None,
            tempo: Optional[float] = None,
            seed: Optional[int] = None,
            prompt_boost: Optional[bool] = None,
            accent_base_locale: Optional[str] = None,
            accent_locale: Optional[str] = None,
            accent_ratio: Optional[float] = None,
            sample_rate: Optional[int] = None,
            format: str = "mp3",
            **kwargs) -> str:
        """
        TTS (Text-to-Speech) endpoint.
        """
        #tempo and duration are mutually exclusive
        assert format in ["headerless-wav", "mp3", "opus", "mulaw"], "Invalid format"
        assert tempo is None or duration is None, "Tempo and duration are mutually exclusive"
        assert voice_reference is not None or voice_prompt_id is not None, "Either voice_reference or voice_prompt_id must be provided"
        if voice_reference is not None:
            voice_reference, _ = self.data_input_preprocess(voice_reference)
        
        assert model in MODEL_LIST or not model.startswith("dd-"), "Invalid model"
        assert [3,0].__contains__(sum([accent_base_locale is not None, accent_locale is not None, accent_ratio is not None])), "All three of accent_base_locale, accent_locale, and accent_ratio must be provided or none of them must be provided"
        assert sample_rate in [None, 8000, 16000, 22050, 24000, 44100, 48000], "Invalid sample rate"

        return self.post(f"/tts", json={
                "targetText": text,
                "model": model,
                "voicePromptId": voice_prompt_id,
                "locale": locale,
                "voiceReference": voice_reference,
                "temperature": temperature,
                "variance": variance,
                "duration": duration,
                "seed": seed,
                "tempo": tempo,
                "promptBoost": prompt_boost,
                "accentControl": {
                    "accentBaseLocale": accent_base_locale,
                    "accentLocale": accent_locale,
                    "accentRatio": accent_ratio
                } if accent_base_locale is not None and accent_locale is not None and accent_ratio is not None else None,
                "sampleRate": sample_rate,
                "format": format,
                **kwargs
            })

    def tts_retro(self, text: str, voice_prompt_id: str, model: str = "dd-etts-2.5", locale: str = "en-US") -> str:
        """
        TTS (Text-to-Speech) endpoint.
        """
        assert model in MODEL_LIST or not model.startswith("dd-"), "Invalid model"
        return self.post("/tts/retroactive", json={
                "targetText": text,
                "model": "dd-etts-2.5",
                "voicePromptId": voice_prompt_id,
                "locale": locale,
            })
    async def gender_classify(self, audio_data: Union[bytes, str, Path], 
            sample_rate: int = 16000, timeout: float = 5.0,
            generation_id: Optional[str] = None) -> dict:
        """
        Classify the gender of a speaker in an audio sample via websocket.
        Audio is automatically trimmed to the first 1 second (API limit).

        Can be used standalone (creates its own connection) or within an
        async_connect() context to multiplex multiple calls on one websocket.

        Args:
            audio_data: Audio data as bytes, base64 encoded string, or Path to audio file
            sample_rate: Sample rate of the audio data
            timeout: Timeout in seconds for the response
            generation_id: Optional UUID for request tracking. Auto-generated if None.

        Returns:
            Dictionary with gender classification result
        """
        audio = AudioSample(audio_data, force_sample_rate=16000)[0:1]
        audio_b64 = base64.b64encode(audio.as_wav_data()).decode()

        if generation_id is None:
            generation_id = str(uuid4())
        else:
            try:
                UUID(generation_id)
            except ValueError:
                raise ValueError(f"Invalid UUID string for generation_id: {generation_id}")

        message = {
            "action": "gender-classify",
            "generationId": generation_id,
            "audio": audio_b64,
            "sample_rate": sample_rate
        }

        if self.websocket is not None:
            await self.websocket.send(json.dumps(message))
            response = await asyncio.wait_for(
                self._ws_default_queue.get(), timeout=timeout)
            if response.get("error"):
                raise Exception(response["error"])
            return response
        else:
            headers = {"x-api-key": self.api_key}
            async with websockets.connect(self.base_websocket_url, additional_headers=headers) as ws:
                await ws.send(json.dumps(message))
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                response = json.loads(raw)
                if response.get("error"):
                    raise Exception(response["error"])
                return response

    async def _ws_listener(self):
        try:
            while True:
                message = await self.websocket.recv()
                if message:
                    try:
                        message = json.loads(message)
                    except Exception:
                        print(f"[_ws_listener] Error parsing message: {message}")
                        raise RuntimeError(f"Error parsing message: {message}")

                    generation_id = message.get("generationId")
                    if generation_id:
                        self._ws_queues[generation_id].put_nowait(message)
                    else:
                        self._ws_default_queue.put_nowait(message)
        except websockets.exceptions.ConnectionClosedOK:
            pass

    @asynccontextmanager
    async def async_connect(self, streaming_input: bool = False):
        headers = {"x-api-key": self.api_key}
        assert self.websocket is None, "Already connected"
        new_client = DeepdubClient(
                base_url=self.base_url,
                base_websocket_url=self.base_websocket_url,
                base_websocket_streaming_url=self.base_websocket_streaming_url,
                api_key=self.api_key
            )
        try:
            async with websockets.connect(self.base_websocket_url if not streaming_input else self.base_websocket_streaming_url, additional_headers=headers) as websocket:

                new_client.websocket = websocket
                if not streaming_input:
                    new_client._ws_queues = defaultdict(asyncio.Queue)
                    new_client._ws_default_queue = asyncio.Queue()
                    new_client._ws_listener_task = asyncio.create_task(new_client._ws_listener())
                else:
                    new_client._ws_queues = None
                    new_client._ws_listener_task = None
                yield new_client
                await new_client.websocket.close()

                if not streaming_input:
                    await new_client._ws_listener_task
                new_client.websocket = None
                new_client._ws_listener_task = None
                new_client._ws_queues = None
        except Exception as e:
            new_client.websocket = None
            raise e

    async def async_tts(self, text: str,
            voice_prompt_id: Optional[str] = None,
            model: str = "dd-etts-2.5",
            locale: str = "en-US",
            temperature: Optional[float] = None,
            variance: Optional[float] = None,
            duration: Optional[float] = None,
            tempo: Optional[float] = None,
            seed: Optional[int] = None,
            prompt_boost: Optional[bool] = None,
            accent_base_locale: Optional[str] = None,
            accent_locale: Optional[str] = None,
            accent_ratio: Optional[float] = None,
            format: str = "wav",
            generation_id: Optional[str] = None,
            sample_rate: Optional[int] = None,
            target_gender: Optional[str] = None,
            verbose: bool = False,
            **kwargs) -> str:
        """
        TTS (Text-to-Speech) endpoint.
        """
        #tempo and duration are mutually exclusive
        assert tempo is None or duration is None, "Tempo and duration are mutually exclusive"
        assert model in MODEL_LIST or not model.startswith("dd-"), "Invalid model"
        assert format in ["headerless-wav", "wav", "mp3", "opus", "mulaw"], "Invalid format"
        headerless = False
        if format == "headerless-wav":
            format = "wav"
            headerless = True
        assert sample_rate in [None, 8000, 16000, 22050, 24000, 44100, 48000], "Invalid sample rate"
        assert [3,0].__contains__(sum([accent_base_locale is not None, accent_locale is not None, accent_ratio is not None])), "All three of accent_base_locale, accent_locale, and accent_ratio must be provided or none of them must be provided"
        # Handle generation_id
        if generation_id is None:
            generation_id = str(uuid4())
        else:
            try:
                UUID(generation_id)  # validate UUID
            except ValueError:
                raise ValueError(f"Invalid UUID string for generation_id: {generation_id}")
        message_to_send = {
                "action": "text-to-speech",
                "generationId": generation_id,
                "targetText": text,
                "model": model,
                "voicePromptId": voice_prompt_id,
                "locale": locale,
                "temperature": temperature,
                "variance": variance,
                "duration": duration,
                "seed": seed,
                "tempo": tempo,
                "promptBoost": prompt_boost,
                "accentControl": {
                    "accentBaseLocale": accent_base_locale,
                    "accentLocale": accent_locale,
                    "accentRatio": accent_ratio
                } if accent_base_locale is not None and accent_locale is not None and accent_ratio is not None else None,
                "format": format,
                "sampleRate": sample_rate,
                "targetGender": target_gender,
                **kwargs
            }
        await self.websocket.send(json.dumps(message_to_send))
        if verbose:
            print(f"sent message {message_to_send}")
        while True:
            message_received = await self._ws_queues[generation_id].get()
            if message_received.get("error"):
                raise Exception(message_received["error"])
            if message_received.get("generationId") != generation_id:
                continue
            if verbose:
                print(f"received chunk {message_received['generationId']} - {message_received.get('index', 'unknown') }")
            if message_received.get("data"):
                if verbose:
                    print(f"received data {message_received['data']}")
                data = base64.b64decode(message_received['data'])
                if format == "wav" and headerless:
                    data = data[self.dd_wav_header_len:]
                yield data
            if message_received.get("isFinished"):
                if verbose:
                    print(f"finished generation {message_received['generationId']}")
                break

    @asynccontextmanager
    async def async_stream_connect(self, model: str, locale: str, voice_prompt_id: str, format: str = "wav", 
        sample_rate: int = 16000, temperature: float = None, variance: float = None, 
        tempo: float = None, prompt_boost: bool = False, 
        accent_base_locale: str = None, accent_locale: str = None, accent_ratio: float = None,
        verbose: bool = False):
        async with self.async_connect(streaming_input=True) as conn:
            response = await conn.async_stream_config(model=model, 
                locale=locale, voice_prompt_id=voice_prompt_id, 
                format=format, sample_rate=sample_rate,     
                temperature=temperature, variance=variance, tempo=tempo, prompt_boost=prompt_boost,
                accent_base_locale=accent_base_locale, accent_locale=accent_locale, accent_ratio=accent_ratio)
            if verbose:
                print(f"config ok: {response}")
            yield conn

    async def async_stream_config(self, model: str, locale: str, voice_prompt_id: str, format: str = "wav", 
    sample_rate: int = 16000, temperature: float = None, variance: float = None, 
    tempo: float = None, prompt_boost: bool = None,
    accent_base_locale: str = None, accent_locale: str = None, accent_ratio: float = None):
        self.streaming_format = format
        message_to_send = {
            "action": "stream-config",
            "config": {
                "model": model,
                "locale": locale,
                "voicePromptId": voice_prompt_id,
                "format": format,
                "sampleRate": sample_rate,
                "temperature": temperature,
                "variance": variance,
                "tempo": tempo,
                "promptBoost": prompt_boost,
                "accentControl": {
                    "accentBaseLocale": accent_base_locale,
                    "accentLocale": accent_locale,
                    "accentRatio": accent_ratio
                } if accent_base_locale is not None and accent_locale is not None and accent_ratio is not None else None,
            }
        }
        await self.websocket.send(json.dumps(message_to_send))
        response = await self.websocket.recv()
        return response

    async def async_stream_text(self, text: str):
        message_to_send = {
            "action": "stream-text",
            "data": { "text": text }
        }
        await self.websocket.send(json.dumps(message_to_send))

    async def async_stream_recv(self):
        response = await self.websocket.recv()
        if not isinstance(response, bytes):
            return None
        response = json.loads(response)
        if response.get("error"):
            raise Exception(response["error"])        
        return response
    
    async def async_stream_recv_audio(self):
        response = await self.async_stream_recv()
        if response and response.get("data"):
            return base64.b64decode(response['data'])
        return None

    @asynccontextmanager
    async def async_stream(self, ignore_errors: bool = False):
        while True:
            response = await self.websocket.recv()
            if response.get("data"):
                data = base64.b64decode(response['data'])
                if self.streaming_format == "wav":
                    data = data[self.dd_wav_header_len:]
                yield data
            if response.get("isFinished"):
                continue
            if response.get("error") and not ignore_errors:
                raise Exception(response["error"])
