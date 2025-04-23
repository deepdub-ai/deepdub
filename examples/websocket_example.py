import asyncio
import sys
from deepdub import DeepdubClient
from audiosample import AudioSample

client = DeepdubClient()


async def main():
    collection = AudioSample()
    async with client.async_connect() as connection:
        async for chunk in connection.async_tts(text="Hello, world!", voice_prompt_id="5d3dc622-69bd-4c00-9513-05df47dbdea6_authoritative"):
            sys.stdout.buffer.write(chunk)
            collection += AudioSample(chunk)
    collection.write("hello_world.wav")

if __name__ == "__main__":
    asyncio.run(main())
