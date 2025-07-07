import base64
import os
from uuid import uuid4
import json
import requests
import websockets
from typing import Dict, List, Any, Optional, Union
from functools import partial
from pathlib import Path
from contextlib import asynccontextmanager

MODEL_LIST = ["dd-etts-2.5", "dd-etts-1.1"]

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

    def __init__(self, base_url: str = "https://restapi.deepdub.ai/api/v1", base_websocket_url: str = "wss://wsapi.deepdub.ai/open", api_key: Optional[str] = None):
        """
        Initialize the DeepDub API client.
        
        Args:
            base_url: Base URL for the DeepDub API
            api_key: API key for authentication (if required)
        """
        self.base_url = base_url
        self.base_websocket_url = base_websocket_url
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
        
        assert model in ["dd-etts-2.5", "dd-etts-1.1"] or not model.startswith("dd-"), "Invalid model"
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
        assert model in ["dd-etts-2.5", "dd-etts-1.1"], "Invalid model"
        return self.post(f"/tts/retroactive", json={
                "targetText": text,
                "model": "dd-etts-2.5",
                "voicePromptId": voice_prompt_id,
                "locale": locale,
            })

    @asynccontextmanager
    async def async_connect(self):
        headers = {"x-api-key": self.api_key}
        assert self.websocket is None, "Already connected"
        try:
            async with websockets.connect(self.base_websocket_url, additional_headers=headers) as websocket:
                self.websocket = websocket
                yield self
                self.websocket = None
        except Exception as e:
            self.websocket = None
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
            sample_rate: Optional[int] = None,
            verbose: bool = False,
            **kwargs) -> str:
        """
        TTS (Text-to-Speech) endpoint.
        """
        #tempo and duration are mutually exclusive
        assert tempo is None or duration is None, "Tempo and duration are mutually exclusive"
        #assert model in ["dd-etts-2.5", "dd-etts-1.1"], "Invalid model"
        assert format in ["headerless-wav", "wav", "mp3", "opus", "mulaw"], "Invalid format"
        if format == "headerless-wav":
            format = "wav"
            headerless = True
        assert sample_rate in [None, 8000, 16000, 22050, 24000, 44100, 48000], "Invalid sample rate"
        assert [3,0].__contains__(sum([accent_base_locale is not None, accent_locale is not None, accent_ratio is not None])), "All three of accent_base_locale, accent_locale, and accent_ratio must be provided or none of them must be provided"
        generation_id = str(uuid4())
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
                **kwargs
            }
        await self.websocket.send(json.dumps(message_to_send))
        if verbose:
            print(f"sent message {message_to_send}")
        while True:
            message_received = await self.websocket.recv()
            message_received = json.loads(message_received)
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
