import asyncio
import discord
import os
import redis
import requests
from discord.ext import commands
from dotenv import load_dotenv
from quickchart import QuickChart
from redis import asyncio as aioredis
from redis import RedisError
from typing import Optional
from gsheets import KvK
from PIL import Image, ImageDraw, ImageFont
import io
import re

store = aioredis.from_url(
    "link",
    encoding="utf-8",
    decode_responses=True,
    port=port,
    password="PW"
)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

REDIS_KEY_GOV_ID = "authorid:govid"
GOV_KEYS = [
    "ID",
    "BASE NAME",
    "BASE POWER",
    "BASE T4 KILLS",
    "BASE T5 KILLS",
    "BASE KILL POINTS",
    "NAME",
    "POWER",
    "KILL POINTS",
    "KVK KILLS | T4",
    "KVK KILLS | T5",
    "KVK Farm Deads",
    "KVK DEADS",
    "KVK DEADS",
    "DKP Goal",
    "DKP Score",
    "DKP Rate",
    "HONOR POINTS",
    "TOTAL SCORE",
    "KVK RANK",
]
GOV_KEYS_BASE = [
    "BASE POWER",
    "T4 KILLS",
    "T5 KILLS",
    "BASE KILL POINTS",
]
GOV_KEYS_CURRENT = [
    "KVK KILLS | T4",
    "KVK KILLS | T5",
    "KVK DEADS",
    "DKP Goal",
    "DKP Score",
    "DKP Rate",
    "T4 Dead Requirement"
]
GOAL_KEYS = {
    "dkpgoal": "DKP Goal",
    "dkpscore": "DKP Score",
    "dkprate": "DKP Rate",
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)


def parse_number_value(value, default=0):
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        clean_value = re.sub(r'[^\d.]', '', value.replace(',', ''))
        try:
            return float(clean_value) if clean_value else default
        except ValueError:
            return default

    return default


def create_progress_bar(rate_value, kvk_deads=None, dkp_score=None):
    try:
        if isinstance(rate_value, str):
            rate_match = re.search(r'(\d+(?:\.\d+)?)%?', rate_value)
            if rate_match:
                percentage = float(rate_match.group(1))
            else:
                percentage = 0
        elif isinstance(rate_value, (int, float)):
            percentage = float(rate_value)
        else:
            percentage = 0

        percentage = min(100, percentage)

        width, height = 500, 60

        img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Colors
        border_color = (210, 180, 222)  # Light purple border
        background_color = (240, 230, 245)  # Very light purple background
        fill_color = (180, 140, 200)  # Medium, not-too-bright purple for fill
        deads_color = (130, 80, 160)  # Darker purple for deads contribution
        draw.rounded_rectangle([(0, 0), (width, height)], radius=10, fill=border_color)

        draw.rounded_rectangle([(2, 2), (width - 2, height - 2)], radius=9, fill=background_color)
        fill_width = int((width - 4) * (percentage / 100))

        deads_width = 0
        deads_percentage = 0
        other_percentage = 0

        if kvk_deads is not None and dkp_score is not None:
            deads_value = parse_number_value(kvk_deads)
            score_value = parse_number_value(dkp_score)

            if score_value > 0:
                deads_contribution = deads_value * 15
                deads_percentage = (deads_contribution / score_value) * 100

                other_percentage = percentage - min(deads_percentage, percentage)

                deads_percentage = min(deads_percentage, percentage)

                deads_width = int((width - 4) * (deads_percentage / 100))

        if fill_width > 0:
            draw.rounded_rectangle([(2, 2), (2 + fill_width, height - 2)], radius=9, fill=fill_color)

            if deads_width > 0:
                draw.rounded_rectangle([(2, 2), (2 + deads_width, height - 2)], radius=9, fill=deads_color)

        try:
            main_font = ImageFont.truetype("arial.ttf", 24)
            label_font = ImageFont.truetype("arial.ttf", 22)
        except IOError:
            main_font = ImageFont.load_default()
            label_font = ImageFont.load_default()

        if deads_width > 20:
            deads_text = f"{deads_percentage:.1f}%"
            deads_text_width = draw.textlength(deads_text, font=label_font)
            deads_text_x = max(5, (deads_width - deads_text_width) // 2)

            text_height = label_font.getsize(deads_text)[1] if hasattr(label_font, 'getsize') else 22
            deads_text_y = (height - text_height) // 2

            draw.text((2 + deads_text_x, deads_text_y), deads_text, font=label_font, fill=(255, 255, 255))

        other_width = fill_width - deads_width
        if other_width > 20:
            other_text = f"{other_percentage:.1f}%"
            other_text_width = draw.textlength(other_text, font=label_font)
            other_text_x = deads_width + (other_width - other_text_width) // 2

            text_height = label_font.getsize(other_text)[1] if hasattr(label_font, 'getsize') else 22
            other_text_y = (height - text_height) // 2

            draw.text((2 + other_text_x, other_text_y), other_text, font=label_font, fill=(255, 255, 255))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return img_byte_arr, deads_percentage, other_percentage
    except Exception as e:
        print(f"Error creating progress bar: {e}")
        return None, 0, 0
async def get_id_from_store(
        authorid: str, gov_id: Optional[int] = None
) -> Optional[int]:
    memory_gov_id = None

    try:
        async with store.client() as conn:
            if gov_id is not None:
                await conn.hset(REDIS_KEY_GOV_ID, authorid, gov_id)
                return gov_id
            memory_gov_id = await conn.hget(REDIS_KEY_GOV_ID, authorid)
    except RedisError as e:
        print(e)

    if memory_gov_id is not None:
        try:
            memory_gov_id = int(memory_gov_id)
        except Exception as e:
            print(e)
            memory_gov_id = None
    return memory_gov_id


async def get_stat_governor_id(
        gov_id: int, interaction: discord.Interaction = None, channel=None
):
    kvk = KvK()
    governor = kvk.get_governor_last_data(gov_id)
    if governor is None:
        content = f"Governor {gov_id} not found in database."
        if interaction:
            return await interaction.response.send_message(content)
        elif channel:
            return await channel.send(content=content)
        else:
            return

    title = f"{governor.get('BASE NAME', '---')} - {governor.get('ID', '---')}"
    embed = discord.Embed(color=0x06B6D4)
    embed.title = title
    base_description = ""
    for k in GOV_KEYS_BASE:
        v = governor.get(k, None)
        base_description += f"**{k.lower().title()}**: {v or '---'}\n"

    base_description += "\n\n"
    base_description += "\n"

    for k in GOV_KEYS_CURRENT:
        v = governor.get(k, None)
        embed.add_field(name=f"**{k.lower().title()}**", value=f"{v or '---'}\n", inline=True)

    base_description += "\n"
    embed.set_footer(text=f"Data collect on: {kvk.get_last_registered_date()}")
    embed.description = base_description

    dkp_rate = governor.get("DKP Rate", "0%")
    kvk_deads = governor.get("KVK DEADS", 0)
    dkp_score = governor.get("DKP Score", 0)

    result = create_progress_bar(dkp_rate, kvk_deads, dkp_score)
    if result and result[0]:
        progress_bar_bytes, deads_percentage, other_percentage = result
        file = discord.File(fp=progress_bar_bytes, filename="progress_bar.png")
        embed.set_image(url="attachment://progress_bar.png")

        if interaction:
            await interaction.response.send_message(embed=embed, file=file)
        elif channel:
            await channel.send(embed=embed, file=file)
    else:
        if interaction:
            await interaction.response.send_message(embed=embed)
        elif channel:
            await channel.send(embed=embed)


@bot.hybrid_command(name="stat")
async def stat(ctx):
    interaction: discord.Interaction = ctx.interaction
    data = interaction.data
    options = data["options"]
    option = options[0]
    value = option["value"]
    gov_id = None

    try:
        gov_id = int(value)
    except Exception as e:
        # maybe not a valid player ID
        print(e)

    if gov_id is None:
        await interaction.response.send_message(
            "Sorry! you entered a non valid GOVERNOR ID", ephemeral=True
        )
    else:
        await get_stat_governor_id(gov_id=gov_id, interaction=interaction)


@bot.hybrid_command(name="top")
async def top(ctx):
    interaction: discord.Interaction = ctx.interaction
    ranking = KvK().get_top_governors(top=100)

    # Sort the ranking list by 'score' in descending order
    ranking = sorted(ranking, key=lambda x: x['score'], reverse=True)

    chunked_list = []
    chunked_size = 20
    for i in range(0, len(ranking), chunked_size):
        chunked_list.append(ranking[i: i + chunked_size])

    embed_list = []
    for idx, chunked in enumerate(chunked_list):
        l = len(chunked)
        start = idx * chunked_size + 1
        end = idx * chunked_size + l

        content = ""
        for i, row in enumerate(chunked):
            content += f"- {'0' if (start + i) < 10 else ''}{start + i} > {row['name']}: {row['score']} = ({row['score']}/{row['goal']} )\n"
        content += ""

        embed = discord.Embed(color=0x0000FF)
        embed.title = f"TOP by TOTAL SCORE \n"
        embed.add_field(name=f"{start} -> {end}", value=content)
        embed_list.append(embed)

    try:
        await interaction.response.send_message(embeds=embed_list)
    except Exception as e:
        await interaction.response.send_message(str(e))


@bot.event
async def on_command_error(ctx, error):
    interaction: discord.Integration = ctx.interaction

    if isinstance(error, commands.MissingRole):
        await interaction.response.send_message(
            content="You don't have appropriate Role", ephemeral=True
        )
    elif isinstance(error, commands.CommandError):
        await interaction.response.send_message(
            content=f"Invalid command {str(error)}", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            content="An error occurred", ephemeral=True
        )


@bot.event
async def on_ready():
    try:
        async with store.client() as conn:
            pong = await conn.ping()
            print(f"Redis ping: {'pong' if pong else '---'}")
    except RedisError as e:
        print(e)


@bot.event
async def on_message(message):
    author = message.author
    author_id = author.id
    content = message.content
    channel = message.channel

    if not content or content.strip() == "":
        return

    gov_id = None

    cmd = content.split(" ")
    cmd_length = len(cmd)
    if cmd_length == 2:
        cmd_name = cmd[0]
        gov_id = cmd[1]
        if cmd_name.lower() != "stat":
            return
        try:
            gov_id = int(gov_id)
        except Exception as e:
            return await channel.send(content="Governor ID is not valid.")
        gov_id = await get_id_from_store(authorid=author_id, gov_id=gov_id)
    elif cmd_length == 1:
        cmd_name = cmd[0]
        if cmd_name.lower() != "stat":
            return
        gov_id = await get_id_from_store(authorid=author_id)
    else:
        return

    if gov_id is None:
        return await channel.send(
            content="Governor ID not found in memory. Please try with the full command: `stat 1234` (where 1234 is your Governor ID)"
        )

    await get_stat_governor_id(gov_id=gov_id, channel=channel)


async def main():
    await bot.start(TOKEN, reconnect=True)


asyncio.run(main())
