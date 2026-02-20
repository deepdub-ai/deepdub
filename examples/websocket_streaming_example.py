import asyncio
import time

from audiosample import AudioSample
import deepdub
import json


async def main():
    dd = deepdub.DeepdubClient()
    async with dd.async_stream_connect(model=os.environ.get("DD_MODEL", "dd-etts-3.0"), locale="en-US",
        voice_prompt_id="408e3a63-d449-4e65-a098-ee18c542ec8e_reading-neutral", 
        sample_rate=16000, format="s16le") as conn:
        # msg = {
        #     "action": "stream-config",
        #     "config": {
        #         "model": "dd-etts-3.0",
        #         "locale": "en-US",
        #         "voicePromptId": "408e3a63-d449-4e65-a098-ee18c542ec8e_reading-neutral",
        #         "sampleRate": 16000
        #     }
        # }
        t1 = time.time()
        ttfa = False
        test_list = "Hello. World!"
        print(f"sending text: {list(test_list)!r}")
        for t in test_list:
            # websocket streaming message format = {
            #     "action": "stream-text",
            #     "data": {"text": t}
            # }
            print(f"sending text: {t}")
            await conn.async_stream_text(text=t)

        audio = AudioSample(force_read_format="s16le", force_read_sample_rate=16000, force_sample_rate=16000)
        while True:
            # raw response format:
            # {
            #     "action": "stream-text",
            #     "data": audio data (base64 encoded)
            #     "isFinished": true/false (if true, temporarily stopped receiving audio)
            #     "error": error message (if any, in which case the connection is closed)
            # }
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
        audio.write("websocket_streaming_example_output_1.wav")
        t1 = time.time()
        ttfa = False
        test_list = ["Hello. ", "World!"]
        print(f"sending text: {test_list!r}")
        for t in test_list:
            # msg = {
            #     "action": "stream-text",
            #     "data": {"text": t}
            # }
            print(f"sending text: {t}")
            await conn.async_stream_text(text=t)

        audio = AudioSample(force_read_format="s16le", force_read_sample_rate=16000, force_sample_rate=16000)
        while True:
            # raw response format:
            # {
            #     "action": "stream-text",
            #     "data": audio data (base64 encoded)
            #     "isFinished": true/false (if true, temporarily stopped receiving audio)
            #     "error": error message (if any, in which case the connection is closed)
            # }
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
        audio.write("websocket_streaming_example_output_2.wav")

if __name__ == "__main__":
    asyncio.run(main())
