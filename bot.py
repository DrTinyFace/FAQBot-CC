# FAQBot-CC
#
# Discord bot for private use only.
# Created by Wendelstein7, https://github.com/FAQBot-CC

from datetime import datetime, date
from typing import Callable, List, Tuple
import json
import logging
import os
import re
import sys

import discord
from discord.ext import commands

import faq_list
import log
from cached_request import CachedRequest

log.configure()

LOG = logging.getLogger("FAQBot-CC")

bot = commands.Bot( command_prefix='%' )
starttime = datetime.utcnow()
faqs: List[Tuple[str, str, str]] = []

# Fetch from tweaked.cc at most once per minute.
cc_methods = CachedRequest(
    60, "https://tweaked.cc/index.json",
    lambda contents: { k.lower(): v for k, v in json.loads(contents).items() }
)

LOG.info("Starting discord Bot")

def msg_should_process( message ):  # do not process bot messages, own messages, non-default messages
    if (message.author.bot) or (message.author.id == bot.user.id) or (message.type is not discord.MessageType.default):  # or (message.guild is None):
        return False
    else:
        return True


@bot.event
async def on_ready():
    LOG.info('Bot: Logged in as %s (id: %s)', bot.user.name, bot.user.id)

@bot.event
async def on_message( message ):
    if msg_should_process( message ):
        await bot.process_commands( message )

@bot.event
async def on_command( ctx ):
    LOG.info('Fired %s by %s', ctx.command, ctx.author)


@bot.command( name='faq', aliases=['f', 'info', 'i'] )
async def faq( ctx, *, search ):
    """Retrieves FAQs related to given keyword(s)."""
    results = []
    for f in faqs:
        if re.search( search, f[0] ):
            results.append( discord.Embed( title=f[1], colour=discord.Colour( 0x00e6e6 ), description=f[2] ) )
    if len( results ) > 0:
        await ctx.send( content="I found the following " + str( len( results ) ) + " faq(s)" )
        for result in results:
            await ctx.send( embed=result )
    else:
        await ctx.send( content="Sorry, I did not find any faqs related to your search.\nPlease contribute to expand my faq list: <https://github.com/Wendelstein7/FAQBot-CC>" )

@faq.error
async def faq_error( ctx, error ):
    if isinstance( error, commands.MissingRequiredArgument ):
        await ctx.send( content="Missing arguments! Please provide keywords to search for." )
    else:
        LOG.error("Error processing faq command: %s", error)
        await ctx.send("An unexpected error occurred when processing the command.")


async def search_docs(ctx, search: str, link: Callable[[dict], str]):
    """Search the documentation with a query and link to the result"""
    methods = await cc_methods.get()
    search_k = search.lower()
    if search_k in methods:
        method = methods[search_k]
        embed = discord.Embed(title=method["name"], url=link(method))
        if "summary" in method:
            embed.description = method["summary"]
        await ctx.send(embed=embed)
    else:
        await ctx.send(content=f"Cannot find method '{search}'. Please check your spelling, or contribute to the documentation at https://github.com/SquidDev-CC/CC-Tweaked.")


@bot.command(name="doc", aliases=["d", "docs"])
async def doc(ctx, *, search: str):
    """Searches for a function with the current name, and returns its documentation."""
    def build_link(value):
        url = f"https://tweaked.cc/module/{value['module']}.html"
        if "section" in value:
            url += f"#{value['section']}"
        return url
    await search_docs(ctx, search, build_link)


@bot.command(name="source", aliases=["s"])
async def source(ctx, *, search: str):
    """Searches for a function with the current name, and returns a link to its source code."""
    await search_docs(ctx, search, lambda x: x["source"])


@doc.error
@source.error
async def doc_error(ctx, error):
    """Reports an error on the source and doc commands."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(content="Missing arguments! Please provide a CC:T method to search for.")
    else:
        LOG.error("Error processing command: %s", error)
        await ctx.send("An unexpected error occurred when processing the command.")


@bot.command( name='about', aliases=[] )
async def about( ctx ):
    """Shows information about the bot as well as the relevant version numbers, uptime and useful links."""
    embed = discord.Embed( title="ComputerCraft FAQ Bot", colour=discord.Colour( 0x00e6e6 ), url="https://github.com/Wendelstein7/FAQBot-CC", description="A Discord bot for answering frequently asked questions regarding CC. Please contribute and expand the list of answers on [GitHub](https://github.com/Wendelstein7/FAQBot-CC)!" )
    embed.set_thumbnail( url=bot.user.avatar_url )
    embed.add_field( name=":information_source: **Commands**", value="Please use the `%help` to list all possible commands.\nUse `%f <search>` to find faqs related to your search.", inline=True )
    embed.add_field( name=":hash: **Developers**", value="**HydroNitrogen** as creator and other contributors mentioned on GitHub.", inline=True )
    embed.add_field( name=":asterisk: **FAQs**", value="Currently there are " + str( len( faqs ) ) + " FAQs loaded into memory.", inline=True)
    embed.add_field( name=":new: **Version information**", value="Bot version: `{}`\nDiscord.py version: `{}`\nPython version: `{}`".format( date.fromtimestamp( os.path.getmtime( 'bot.py' ) ), discord.__version__, sys.version.split( ' ' )[0] ), inline=True )
    embed.add_field( name=":up: **Uptime information**", value="Bot started: `{}`\nBot uptime: `{}`".format( starttime.strftime( "%Y-%m-%d %H:%M:%S UTC" ), (datetime.utcnow().replace( microsecond=0 ) - starttime.replace( microsecond=0 )) ), inline=True )
    await ctx.send( embed=embed )

for faq in faq_list.FAQS:
    try:
        LOG.info('Loading faqs/%s', faq[2])
        file = open( 'faqs/' + faq[2] )
        faqs.append( (faq[0], faq[1], file.read().strip()) )
    except IOError:
        LOG.error( 'An error occurred when reading faq file...' )
    finally:
        file.close()

LOG.info('Successfully loaded %d FAQs!', len(faqs))

with open( 'token', 'r' ) as file:
    content = file.read().strip()

bot.run( content )
