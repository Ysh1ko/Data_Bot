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

store = aioredis.from_url(
    "LINK",
    encoding="ENCODING",
    decode_responses=True,
    port=PORT,
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

def get_chart_url(progress=0):
    qc = QuickChart()
    qc.width = 500
    qc.height = 300
    qc.version = "2.9.4"
    qc.config = """{
        type: 'gauge',
        data: {
            datasets: [
            {
                value: %i,
                data: [50, 100, 150, 200],
                backgroundColor: ['#D64545', '#4098D7', '#3EBD93', 'black'],
                borderWidth: 2,
            },
            ],
        },
        options: {
            valueLabel: {
            fontSize: 24,
            backgroundColor: 'transparent',
            color: '#000',
            formatter: function (value, context) {
                return %i + ' %%';
            },
            bottomMarginPercentage: 10,
            },
        },
        }""" % (
        progress if progress <= 200 else 200,
        progress,
    )
    return qc.get_url()


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

    gov_goal_set = True
    for _, v in GOAL_KEYS.items():
        if v not in governor:
            gov_goal_set = False

    if interaction:
        await interaction.response.send_message(embed=embed)
    elif channel:
        await channel.send(embed=embed)


@bot.hybrid_command(name="stat")
async def stat(ctx):
    interaction: discord.Interaction = ctx.interaction
    data = interaction.data
    # for the stats command, with only have one option (PLAYER ID)
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
