import discord
import asyncio

TOKEN = 'Token'

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

async def main():
    try:
        await bot.start(TOKEN)
    except discord.errors.LoginFailure as e:
        print(f'Failed to log in: {e}')
    except Exception as e:
        print(f'An error occurred: {e}')
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())
