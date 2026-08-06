import asyncio
import time
import os
from audiosample import AudioSample
import deepdub
import json


async def main():
    # eu=True targets the EU streaming endpoint: wss://wss.eu.deepdub.ai/ws
    dd = deepdub.DeepdubClient(eu=True)
    print("Streaming connecting (EU)....")
    async with dd.async_stream_connect(model=os.environ.get("DD_MODEL", "dd-etts-3.3"), locale="es-MX",
        voice_prompt_id="408e3a63-d449-4e65-a098-ee18c542ec8e_reading-neutral",
        sample_rate=16000, format="s16le") as conn:
        t1 = time.time()
        ttfa = False
        test_list = "Hello. World!"
        print(f"sending text: {list(test_list)!r}")
        for t in test_list:
            print(f"sending text: {t}")
            await conn.async_stream_text(text=t)
        audio = AudioSample(force_read_format="s16le", force_read_sample_rate=16000, force_sample_rate=16000)
        while True:
            wait_task = asyncio.create_task(conn.async_stream_recv_audio())
            try:
                chunk = await asyncio.wait_for(wait_task, timeout=2)
                if not ttfa:
                    ttfa = True
                    print(f"TTFA: {time.time() - t1}")
                audio += AudioSample(chunk, force_read_format="s16le", force_read_sample_rate=16000, force_sample_rate=16000)
            except asyncio.TimeoutError:
                print(f"Timeout, stopping after {time.time() - t1} seconds")
                break
        audio.write("websocket_streaming_example_eu_output.wav")


if __name__ == "__main__":
    asyncio.run(main())
