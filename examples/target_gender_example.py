"""
Example demonstrating the target_gender parameter with Hebrew text.

This example shows how to use target_gender to control the gender
of the synthesized voice output.
"""
import asyncio
import sys
import os
from deepdub import DeepdubClient
from audiosample import AudioSample

client = DeepdubClient()

# Hebrew text: "Hello, this is a test in Hebrew"
HEBREW_TEXT = "שלום, אני רואה שיש לך מחשב"
HEBREW_TEXT = "שלום, אני רואה ששלומך בסדר"
HEBREW_TEXT2 = "שלום, אני מבקש לך לך"
VOICE_PROMPT_ID = "ef1f4330-5d02-4459-8570-d4499df100bf_reading-neutral" #tamar levi.
VOICE_PROMPT_ID_MALE = "8ce8efb6-26f4-4613-9ebb-d616ace449b3_reading-neutral" #eli weiss


async def generate_with_target_gender(text: str, source_gender: str, target_gender: str, output_file: str):
    """Generate TTS with specified target gender."""
    collection = AudioSample()
    async with client.async_connect() as connection:
        async for chunk in connection.async_tts(
            text=text,
            model=os.environ.get("DD_MODEL"),
            voice_prompt_id=VOICE_PROMPT_ID if source_gender == "female" else VOICE_PROMPT_ID_MALE,
            locale="he-IL",
            target_gender=target_gender,
            realtime=True,
        ):
            collection += AudioSample(chunk)
    collection.write(output_file)
    print(f"\nSaved {target_gender} voice to {output_file}")


async def main():
    await generate_with_target_gender(
        text=HEBREW_TEXT,
        source_gender="female",
        target_gender="male",
        output_file="hebrew_female_to_male.wav"
    )
    await generate_with_target_gender(
        text=HEBREW_TEXT,
        source_gender="male",
        target_gender="female",
        output_file="hebrew_male_to_female.wav"
    )

    await generate_with_target_gender(
        text=HEBREW_TEXT,
        source_gender="female",
        target_gender="female",
        output_file="hebrew_female_to_female.wav"
    )
    await generate_with_target_gender(
        text=HEBREW_TEXT,
        source_gender="male",
        target_gender="male",
        output_file="hebrew_male_to_male.wav"
    )
    await generate_with_target_gender(
        text=HEBREW_TEXT2,
        source_gender="male",
        target_gender="male",
        output_file="go_go_hebrew_male_to_male.wav"
    )


if __name__ == "__main__":
    asyncio.run(main())
