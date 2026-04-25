import discord
from discord.ext import commands, tasks
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def get_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def save_config(data):
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=4)

API_URL = os.getenv("API_URL", "http://localhost:3000/api/newadded")
STATE_FILE = os.path.join(os.path.dirname(__file__), 'last_seen.json')

def get_last_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f).get('lastSeenId')
    return None

def set_last_seen(last_seen_id):
    with open(STATE_FILE, 'w') as f:
        json.dump({'lastSeenId': last_seen_id}, f)

@tasks.loop(minutes=5)
async def check_for_new_episodes():
    config = get_config()
    channel_id = config.get("announcementChannel")
    if not channel_id:
        return

    try:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return

        response = requests.get(API_URL).json()
        if not response.get('success') or not response.get('results'):
            return

        latest_episodes = response.get('results')
        new_episodes = []
        last_seen = get_last_seen()

        for ep in latest_episodes:
            unique_id = f"{ep['anime_id']}-s{ep.get('season', 1)}-e{ep.get('episode', 1)}"
            if unique_id == last_seen:
                break
            new_episodes.insert(0, ep)

        if new_episodes:
            for ep in new_episodes:
                unique_id = f"{ep['anime_id']}-s{ep.get('season', 1)}-e{ep.get('episode', 1)}"
                
                embed = discord.Embed(
                    title=f"New Episode Released: {ep['title']}",
                    description=f"**Season:** {ep.get('season', 1)} | **Episode:** {ep.get('episode', 1)}",
                    color=0xFF4500
                )
                if ep.get('poster'):
                    embed.set_image(url=ep['poster'])
                embed.set_footer(text='KagePlay Anime Bot')

                ping_role = config.get("pingRole")
                ping_text = f"<@&{ping_role}>" if ping_role else ""
                
                await channel.send(content=f"{ping_text} A new episode is out!", embed=embed)
                set_last_seen(unique_id)

    except Exception as e:
        print(f"Anime Checker Error: {e}")

@bot.event
async def on_ready():
    print(f'Bot Logged in as {bot.user}!')
    if not check_for_new_episodes.is_running():
        check_for_new_episodes.start()

@bot.event
async def on_member_join(member):
    config = get_config()
    welcome_channel = config.get("welcomeChannel")
    if welcome_channel and config.get("welcomeMessage"):
        channel = member.guild.get_channel(int(welcome_channel))
        if channel:
            msg = config.get("welcomeMessage").replace('{user}', member.mention)
            
            reaction = config.get("welcomeReaction", "celebrate")
            gif_url = None
            try:
                res = requests.get(f"https://api.otakugifs.xyz/gif?reaction={reaction}&format=gif").json()
                gif_url = res.get('url')
            except:
                pass

            if gif_url:
                embed = discord.Embed(description=msg, color=0x00FF00)
                embed.set_image(url=gif_url)
                await channel.send(content=member.mention, embed=embed)
            else:
                await channel.send(msg)

@bot.event
async def on_member_remove(member):
    config = get_config()
    leave_channel = config.get("leaveChannel")
    if leave_channel and config.get("leaveMessage"):
        channel = member.guild.get_channel(int(leave_channel))
        if channel:
            msg = config.get("leaveMessage").replace('{user}', f"**{member.name}**")
            await channel.send(msg)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_config()
        category_id = config.get("ticketCategory")
        
        ticket_name = f"ticket-{interaction.user.name.lower()}"
        existing = discord.utils.get(interaction.guild.channels, name=ticket_name)
        if existing:
            return await interaction.response.send_message(f"You already have a ticket open: {existing.mention}", ephemeral=True)
            
        category = discord.utils.get(interaction.guild.categories, id=int(category_id)) if category_id else None
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        channel = await interaction.guild.create_text_channel(name=ticket_name, category=category, overwrites=overwrites)
        
        embed = discord.Embed(
            title="Support Ticket",
            description=f"Hello {interaction.user.mention}, please describe your issue here. Support will be with you shortly.",
            color=0x00FF00
        )
        
        view = CloseTicketView()
        await channel.send(content=interaction.user.mention, embed=embed, view=view)
        await interaction.response.send_message(f"Ticket created! {channel.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket in 5 seconds...")
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def setuptickets(ctx):
    embed = discord.Embed(
        title="Support Tickets",
        description="Click the button below to open a support ticket.",
        color=0x0099ff
    )
    await ctx.send(embed=embed, view=TicketView())
    await ctx.message.delete()

def start_bot(token):
    # Setup persistent views
    bot.setup_hook = lambda: bot.add_view(TicketView()) or bot.add_view(CloseTicketView())
    bot.run(token)
