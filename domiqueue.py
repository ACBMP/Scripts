from util import *
import discord as discord

embed_id = 0
channel_id = 0

async def start_queue(message):
    embed = discord.Embed(title="Queue", color=0xff00ff)
    embed.add_field(name="Current players", value="")
    return await message.channel.send(embed=embed)


async def update_queue(message_id):
    await client.wait_until_ready()
    while not client.is_closed():
        message = await client.get_channel(channelId).fetch_message(messageId)


@client.event
async def on_raw_reaction_add(payload):
    if payload.channel_id == channel_id:
        if payload.emoji.name == ":shark:"
            channel = client.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            reaction = get(message.reactions, emoji=payload.emoji.name)
            if reaction and reaction.count > 4:
                await message.delete()
