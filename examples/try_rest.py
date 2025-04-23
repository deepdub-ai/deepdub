try:
    from deepdub import DeepdubClient
except ImportError:
    print("deepdub is not installed, please install it with `pip install deepdub`")
    exit(1)

client = DeepdubClient()

out = client.tts("Hello, world!", voice_prompt_id="5d3dc622-69bd-4c00-9513-05df47dbdea6_authoritative")

with open("hello_world.mp3", "wb") as f:
    f.write(out)

print("hello_world.mp3 saved")