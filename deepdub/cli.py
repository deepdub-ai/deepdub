import time
import datetime
import sys
import asyncio
import click
from pprint import pprint
from deepdub import DeepdubClient
from pathlib import Path

@click.group()
@click.option("--api-key", type=str, help="API key for authentication", envvar="DEEPDUB_API_KEY")
@click.pass_context
def cli(ctx, api_key: str):
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key

@cli.command()
@click.pass_context
def list_voices(ctx):
    client = DeepdubClient(api_key=ctx.obj["api_key"])
    pprint(client.list_voices())

@cli.command()
@click.option("--file", type=str, help="Data of the voice", required=True)
@click.option("--name", type=str, help="Name of the voice", required=True)
@click.option("--gender", type=str, help="Gender of the voice", required=True)
@click.option("--locale", type=str, help="Locale of the voice", required=True)
@click.option("--publish", type=bool, help="Publish the voice", default=True)
@click.option("--speaking-style", type=str, help="Speaking style of the voice", default="Neutral")
@click.option("--age", type=int, help="Age of the voice", default=0)
@click.pass_context
def add_voice(ctx, file: str, name: str, gender: str, locale: str, publish: bool, speaking_style: str, age: int):
    client = DeepdubClient(api_key=ctx.obj["api_key"])
    pprint(client.add_voice(data=Path(file), name=name, gender=gender, locale=locale, publish=publish, speaking_style=speaking_style, age=age))

@cli.command()
@click.option("--text", type=str, help="Text to be converted to speech", required=True)
@click.option("--voice-prompt-id", type=str, help="Voice ID of the voice to be used for the TTS", default="5d3dc622-69bd-4c00-9513-05df47dbdea6_authoritative")
@click.option("--locale", type=str, help="Locale of the voice", default="en-US")
@click.option("--model", type=str, help="Model to be used for the TTS", default="dd-etts-2.5")
@click.pass_context
def tts(ctx, text: str, voice_prompt_id: str, locale: str, model: str):
    client = DeepdubClient(api_key=ctx.obj["api_key"])
    response = client.tts(text=text, voice_prompt_id=voice_prompt_id, locale=locale, model=model)
    fname = f"Deepdub-{text.replace(' ', '-')}-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.mp3".replace('"',"").replace("<","").replace(">","").replace("/","")
    with open(fname, "wb") as f:
        f.write(response)
    print(f"TTS response saved to {fname}")

@cli.command()
@click.option("--text", type=str, help="Text to be converted to speech", required=True)
@click.option("--voice-reference", type=str, help="Audio file with voice reference data be used for the TTS", required=True)
@click.option("--locale", type=str, help="Locale of the voice", default="en-US")
@click.option("--model", type=str, help="Model to be used for the TTS", default="dd-etts-2.5")
@click.pass_context
def tts_from_ref(ctx, text: str, voice_reference: str, locale: str, model: str):
    client = DeepdubClient(api_key=ctx.obj["api_key"])
    response = client.tts(text=text, voice_reference=Path(voice_reference), locale=locale, model=model)
    fname = f"Deepdub-{text.replace(' ', '-')}-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.mp3".replace('"',"").replace("<","").replace(">","").replace("/","")
    with open(fname, "wb") as f:
        f.write(response if isinstance(response, bytes) else str(response).encode("utf-8"))
    print(f"TTS response saved to {fname}")

@cli.command()
@click.option("--text", type=str, help="Text to be converted to speech", required=True)
@click.option("--voice-prompt-id", type=str, help="Voice ID of the voice to be used for the TTS", default="5d3dc622-69bd-4c00-9513-05df47dbdea6_authoritative")
@click.option("--locale", type=str, help="Locale of the voice", default="en-US")
@click.option("--model", type=str, help="Model to be used for the TTS", default="dd-etts-2.5")
@click.pass_context
def tts_retro(ctx, text: str, voice_prompt_id: str, locale: str, model: str):
    client = DeepdubClient(api_key=ctx.obj["api_key"])
    response = client.tts_retro(text=text, voice_prompt_id=voice_prompt_id, locale=locale, model=model)
    print(f"URL: {response['url']}")


async def do_async_tts(client: DeepdubClient, text: str, voice_prompt_id: str, locale: str, model: str, format: str, sample_rate: int, headerless: bool):
    async with client.async_connect() as connection:
        async for chunk in connection.async_tts(text=text, voice_prompt_id=voice_prompt_id, locale=locale, model=model, format=format, sample_rate=sample_rate, headerless=headerless):
            sys.stdout.buffer.write(chunk)

@cli.command()
@click.option("--text", type=str, help="Text to be converted to speech", required=True)
@click.option("--voice-prompt-id", type=str, help="Voice ID of the voice to be used for the TTS", default="5d3dc622-69bd-4c00-9513-05df47dbdea6_authoritative")
@click.option("--locale", type=str, help="Locale of the voice", default="en-US")
@click.option("--model", type=str, help="Model to be used for the TTS", default="dd-etts-2.5")
@click.option("--format", type=str, help="Format of the output audio", default="wav")
@click.option("--sample-rate", type=int, help="Sample rate of the output audio", default=48000)
@click.option("--headerless", type=bool, help="Whether to include the WAV header", is_flag=True, default=False)
@click.option("--verbose", type=bool, help="Whether to print verbose output", is_flag=True, default=False)
@click.pass_context
def tts_async(ctx, text: str, voice_prompt_id: str, locale: str, model: str, format: str, sample_rate: int, headerless: bool, verbose: bool):
    client = DeepdubClient(api_key=ctx.obj["api_key"])
    asyncio.run(do_async_tts(client, text, voice_prompt_id, locale, model, format, sample_rate, headerless))

def main():
    cli(obj={})

if __name__ == "__main__":
    main()
