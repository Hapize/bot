import nextcord
from nextcord.ext import commands, tasks
from pymongo import MongoClient
import os
import re
from datetime import datetime, timedelta
import random
from nextcord import Interaction
import string






TOKEN = "MY_TOKEN"
MONGO_URI = "MY_URI"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client['discord_bot_db']
restricted_users = db['restricted_users']
invite_collection = db['invites']  # Collection to store invite data
streamers_collection = db['streamers']
users = db['users']




# Setup intents
intents = nextcord.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

INFO_CHANNEL_ID = 1298507002850443274  # Set your info channel ID
INVITE_LOG_CHANNEL_ID = 1285236181423882383  
MESSAGE_LOG_CHANNEL_ID = 1287291270569525281
VOICE_LOG_CHANNEL_ID = 1287287186038984724

user_voice_data = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Bot is ready.")

    

    # Cache invites for all guilds in MongoDB
    for guild in bot.guilds:
        await cache_invites(guild)
    print("Invite cache loaded into MongoDB.")


# Define your filters and rules

LINK_REGEX = re.compile(r"https?://\S+")
ALLOWED_DOMAINS = [
        "store.steampowered.com",  # Steam Store
        "steamcommunity.com",        # Steam Community
        "steamid.net",               # Steam ID and profiles
        "youtube.com",               # YouTube
        "youtu.be",                  # YouTube shortened
        "m.youtube.com",             # YouTube mobile
        "instagram.com",             # Instagram
        "www.instagram.com",         # Instagram full links
        "tenor.com",                 # Tenor
        "g.tenor.com",               # Tenor direct GIF links
        "cdn.discordapp.com",
        "discord.com",
        "discordapp.com"
    ]  
ALLOWED_ROLE_IDS = [1239405825739587646]  # Add role IDs here  
CAPSLOCK_THRESHOLD = 0.7  # 70% caps for detection

# Spam Protection
SPAM_LIMIT = 5  # Number of messages allowed per interval
SPAM_INTERVAL = 10  # Interval in seconds
user_message_counts = {}
user_last_message_time = {}

# Raid Protection
RAID_THRESHOLD = 5  # Number of new members that triggers raid protection
RAID_INTERVAL = 60  # Interval in seconds
recent_member_joins = []




async def cache_invites(guild):
    """Fetch and store all invites in the database for the given guild."""
    invites = await guild.invites()
    for invite in invites:
        invite_collection.update_one(
            {"guild_id": guild.id, "invite_code": invite.code},
            {"$set": {"inviter_id": invite.inviter.id, "uses": invite.uses}},
            upsert=True
        )


# Function to check if the link belongs to an allowed domain
def is_allowed_domain(url: str) -> bool:
    for domain in ALLOWED_DOMAINS:
        if domain in url:
            return True
    return False


@bot.event
async def on_message(message: nextcord.Message):
    if message.author.bot:
        return

    # Caps lock detection
    if is_capslock(message.content):
        await message.delete()
        await message.channel.send(
            f"**⚠️ Warning!**\n"
            f"{message.author.mention}, please avoid using excessive caps lock.\n"
            f"Your message has been deleted.",
            delete_after=10
        )
        return

    # Link filtering
    if LINK_REGEX.search(message.content):
        # Check if user has allowed roles (by role ID)
        if any(role.id in ALLOWED_ROLE_IDS for role in message.author.roles):
            return  # Allowed to post links, so return early

        # Check if the link contains an allowed domain
        urls = LINK_REGEX.findall(message.content)
        for url in urls:
            if is_allowed_domain(url):
                return  # The domain is allowed, so return early

        # If no allowed domain or role, delete the message
        await message.delete()
        await message.channel.send(
            f"**🚫 Link Sharing Not Allowed!**\n"
            f"{message.author.mention}, sharing links is not permitted in this channel.\n"
            f"Your message has been deleted.",
            delete_after=10
        )
        return

    

    # Spam protection
    now = datetime.now()
    user_id = message.author.id

    if user_id not in user_message_counts:
        user_message_counts[user_id] = 1
        user_last_message_time[user_id] = now
    else:
        last_message_time = user_last_message_time[user_id]
        if (now - last_message_time).total_seconds() <= SPAM_INTERVAL:
            user_message_counts[user_id] += 1
        else:
            user_message_counts[user_id] = 1

        user_last_message_time[user_id] = now

    if user_message_counts[user_id] > SPAM_LIMIT:
        await message.delete()
        await message.channel.send(
            f"**⚠️ Slow Down!**\n"
            f"{message.author.mention}, you are sending messages too quickly. Please slow down.\n"
            f"Your message has been deleted.",
            delete_after=10
        )
        return

    

@bot.event
async def on_member_join(member: nextcord.Member):
    global recent_member_joins
    current_time = datetime.now()

    # Check for raid
    recent_member_joins = [join_time for join_time in recent_member_joins if (current_time - join_time).total_seconds() < RAID_INTERVAL]
    recent_member_joins.append(current_time)

    if len(recent_member_joins) > RAID_THRESHOLD:
        await member.guild.ban(member, reason="Potential raid detected.")
        
        await member.guild.system_channel.send(f"{member.mention} was banned due to suspected raid activity.")



    # joining role
    role_on_join = member.guild.get_role(1260246472642007162)
    if role_on_join:
        await member.add_roles(role_on_join)
        
    else:
        return



    welcome_channel = bot.get_channel(1270976889451708559)  # Fetch the welcome channel using the ID
    if welcome_channel:
        embed = nextcord.Embed(
            title="🎮 Welcome to the Gaming Realm! 🎮",
            description=f"**Hey {member.mention}!**\n\n"
                        f"Welcome to **{member.guild.name}**! Get ready for an epic adventure with fellow gamers. 🎉\n\n"
                        f"**🔹 Get Started:**\n"
                        f"Make sure to check out the **rules** and introduce yourself \n\n"
                        f"**🔹 Need Help?**\n"
                        f"Don’t hesitate to ask any questions in the **Chatter Box** or ping a moderator! 🚀",
            color=nextcord.Color.from_rgb(0, 128, 255),  # Blue color
            timestamp=datetime.now()
        )
        
        # Add a thumbnail (server logo)
        embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else "https://cdn.discordapp.com/attachments/1234843618896777278/1243796825094361198/New_Project_86_20A64A9.gif?ex=66e9128f&is=66e7c10f&hm=4268ecbc1a6e3052915d145a33967c2673ff3e2470da8be00ca4462595839491&")
        
        # Add fields for a gaming touch
        embed.add_field(name="🎮 Game On!", value="Join our voice channels for some gaming sessions!", inline=False)
        embed.add_field(name="🎉 Events and Tournaments", value="Stay tuned for upcoming events and tournaments!", inline=False)
        
        # Add footer with server name
        embed.set_footer(text=f"Enjoy your stay in {member.guild.name}! 👾", icon_url=member.guild.icon.url if member.guild.icon else "https://cdn.discordapp.com/attachments/1234843618896777278/1243796825094361198/New_Project_86_20A64A9.gif?ex=66e9128f&is=66e7c10f&hm=4268ecbc1a6e3052915d145a33967c2673ff3e2470da8be00ca4462595839491&")
        
        # Add an eye-catching image or GIF
        embed.set_image(url="https://cdn.discordapp.com/attachments/1234843618896777278/1285229220628267141/DARK_REIGN.gif?ex=66e9827c&is=66e830fc&hm=41655fc08500591cfa660e138c90acc5237fcc26b3dd0ff7fed3d28676dbcdf2&")

        # Send the embed to the welcome channel
        await welcome_channel.send(embed=embed)



        # invite logging 

    guild = member.guild
    invites = await guild.invites()

    for invite in invites:
        # Retrieve invite data from MongoDB
        db_invite = invite_collection.find_one({"guild_id": guild.id, "invite_code": invite.code})

        if db_invite and db_invite["uses"] < invite.uses:
            inviter = guild.get_member(db_invite["inviter_id"])
            invite_code = invite.code
            invite_uses = invite.uses

            # Log the invite in the invite log channel
            invite_log_channel = bot.get_channel(INVITE_LOG_CHANNEL_ID)
            if invite_log_channel:
                embed = nextcord.Embed(
                    title="🎉 New Member Alert! 🎉",
                    description=f"**{member.mention}** has joined the server! 🚀\n"
                                f"Invited by: **{inviter.mention}** using invite code: `{invite_code}`.",
                    color=nextcord.Color.from_rgb(0, 204, 0),  # Bright green color for positive events
                    timestamp=datetime.now()
                )
                embed.add_field(name="📈 Total Invites", value=f"**{invite_uses}** invites used with this code!", inline=True)
                
                # Add a footer with inviter's name
                embed.set_footer(text=f"Invited by {inviter.name}!", icon_url=inviter.avatar.url if inviter.avatar else None)
                
                # Optional: Add a thumbnail or image for extra flair (like a server logo)
                embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else "https://cdn.discordapp.com/attachments/1234843618896777278/1243796825094361198/New_Project_86_20A64A9.gif?ex=66e9128f&is=66e7c10f&hm=4268ecbc1a6e3052915d145a33967c2673ff3e2470da8be00ca4462595839491&")
                
                # Send the embed to the invite log channel
                await invite_log_channel.send(embed=embed)

            # Update MongoDB with new invite uses
            invite_collection.update_one(
                {"guild_id": guild.id, "invite_code": invite_code},
                {"$set": {"uses": invite_uses}},
            )
            break


@bot.event
async def on_guild_join(guild: nextcord.Guild):
    # Cache invites in MongoDB when the bot joins a new guild
    await cache_invites(guild)

@bot.event
async def on_invite_create(invite: nextcord.Invite):
    # Add the new invite to the database
    invite_collection.update_one(
        {"guild_id": invite.guild.id, "invite_code": invite.code},
        {"$set": {"inviter_id": invite.inviter.id, "uses": invite.uses}},
        upsert=True
    )

@bot.event
async def on_invite_delete(invite: nextcord.Invite):
    # Remove the invite from the database when it's deleted
    invite_collection.delete_one({"guild_id": invite.guild.id, "invite_code": invite.code})


        
@bot.event
async def on_member_remove(member: nextcord.Member):
    global recent_member_joins
    recent_member_joins = [join_time for join_time in recent_member_joins if join_time != member.joined_at]
    leave_channel = bot.get_channel(1296424259882848287)  # Replace with your leave channel ID
    if leave_channel:
        embed = nextcord.Embed(
            title="😢 Goodbye!",
            description=f"{member.name} has left the server. We'll miss you!",
            color=nextcord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Add a thumbnail (optional)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)

        # Add fields for a personal touch
        embed.add_field(name="We Appreciate You!", value="Thanks for being a part of our community! Your contributions meant a lot to us!", inline=False)
        embed.add_field(name="Keep in Touch!", value="Feel free to rejoin us anytime. Our doors are always open!", inline=False)

        # Add footer
        embed.set_footer(text="Good luck on your adventures!", icon_url="https://cdn.discordapp.com/attachments/1234843618896777278/1243796825094361198/New_Project_86_20A64A9.gif?ex=66e9128f&is=66e7c10f&hm=4268ecbc1a6e3052915d145a33967c2673ff3e2470da8be00ca4462595839491&")

        # Send the embed to the leave channel
        await leave_channel.send(embed=embed)

def is_capslock(content: str) -> bool:
    uppercase_count = sum(1 for c in content if c.isupper())
    return (uppercase_count / len(content)) > CAPSLOCK_THRESHOLD if len(content) > 0 else False

def contains_banned_words(content: str) -> bool:
    content_words = set(content.lower().split())



def format_duration(duration):
    # Convert the duration to seconds, minutes, hours, etc.
    seconds = duration.total_seconds()
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    time_str = []
    if hours > 0:
        time_str.append(f"{hours} hr" + ("s" if hours > 1 else ""))
    if minutes > 0:
        time_str.append(f"{minutes} min" + ("s" if minutes > 1 else ""))
    if seconds > 0:
        time_str.append(f"{seconds} sec" + ("s" if seconds > 1 else ""))

    return ", ".join(time_str) if time_str else "0 sec"

@bot.event
async def on_voice_state_update(member, before, after):
    log_channel = bot.get_channel(VOICE_LOG_CHANNEL_ID)
    current_time = datetime.now().strftime("%Y-%m-%d")
    current_time_with_seconds = datetime.now().strftime("%H:%M:%S")
    user_id = member.id
    user_name = member.name

    def find_mover(before, after):
        # Check if the user was moved by another member
        for m in before.channel.members:
            if m != member and m.voice.channel == after.channel:
                return m.name  # Return the name of the member who moved the user
        return None  # Return None if no one moved the user

    # When user joins a voice channel
    if before.channel is None and after.channel is not None:
        user_voice_data[user_id] = {'joined': datetime.now(), 'channel': after.channel}
        await log_channel.send(f"```----- VOICE LOG -----\n"
                               f"User: {user_name}\n"
                               f"Action: Joined\n"
                               f"Channel: {after.channel.name}\n"
                               f"Date: {current_time}\n"
                               f"Time: {current_time_with_seconds}\n"
                               f"---------------------```")

    # When user leaves a voice channel
    elif before.channel is not None and after.channel is None:
        if user_id in user_voice_data:
            joined_time = user_voice_data[user_id]['joined']
            total_time = datetime.now() - joined_time
            formatted_time = format_duration(total_time)
            await log_channel.send(f"```----- VOICE LOG -----\n"
                                   f"User: {user_name}\n"
                                   f"Action: Left\n"
                                   f"Channel: {before.channel.name}\n"
                                   f"Date: {current_time}\n"
                                   f"Time: {current_time_with_seconds}\n"
                                   f"Total Time Spent: {formatted_time}\n"
                                   f"---------------------```")
            del user_voice_data[user_id]

    # When user moves between voice channels
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        if user_id in user_voice_data:
            joined_time = user_voice_data[user_id]['joined']
            total_time = datetime.now() - joined_time
            formatted_time = format_duration(total_time)

            mover_name = find_mover(before, after)
            moved_text = f"Moved (By {mover_name})" if mover_name else "Moved (By user)"
            await log_channel.send(f"```----- VOICE LOG -----\n"
                                   f"User: {user_name}\n"
                                   f"Action: {moved_text}\n"
                                   f"From: {before.channel.name}\n"
                                   f"To: {after.channel.name}\n"
                                   f"Date: {current_time}\n"
                                   f"Time: {current_time_with_seconds}\n"
                                   f"Time Spent in {before.channel.name}: {formatted_time}\n"
                                   f"---------------------```")

        # Reset join time and update user voice data
        user_voice_data[user_id] = {'joined': datetime.now(), 'channel': after.channel}



# Message Delete Logging
@bot.event
async def on_message_delete(message):
    log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if message.author.bot:
        return  # Ignore messages sent by bots

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = (
        f"```md\n"
        f"## 🗑️ Message Deleted\n"
        f"**Author:** {message.author} ({message.author.id})\n"
        f"**Channel Name:** {message.channel.name}\n"
        f"**Channel ID:** {message.channel.id}\n"
        f"**Content:** {message.content or 'No content (likely an embed or attachment)'}\n"
        f"**Time:** {current_time}\n"
        f"```"
    )
    await log_channel.send(log_message)

# Message Edit Logging
@bot.event
async def on_message_edit(before, after):
    log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if before.author.bot:
        return  # Ignore messages sent by bots

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if before.content == after.content:
        return  # Ignore edits that don't change the message content

    log_message = (
        f"```md\n"
        f"## ✏️ Message Edited\n"
        f"**Author:** {before.author} ({before.author.id})\n"
        f"**Channel Name:** {before.channel.name}\n"
        f"**Channel ID:** {before.channel.id}\n"
        f"**Before:** {before.content or 'No content'}\n"
        f"**After:** {after.content or 'No content'}\n"
        f"**Time:** {current_time}\n"
        f"```"
    )
    await log_channel.send(log_message)


@bot.slash_command(name="restrict", description="Restrict a user by removing their roles and adding a restricted role.")
@commands.has_permissions(manage_roles=True)
async def restrict(interaction: nextcord.Interaction, member: nextcord.Member):
    guild = interaction.guild
    restricted_role_name = "Restricted"
    
    # Check if the restricted role exists, if not, create it
    restricted_role = nextcord.utils.get(guild.roles, name=restricted_role_name)
    
    if restricted_role is None:
        restricted_role = await guild.create_role(
            name=restricted_role_name,
            permissions=nextcord.Permissions.none(),
            reason="Created restricted role"
        )
        
        # Remove access to all channels for this role
        for channel in guild.channels:
            await channel.set_permissions(restricted_role, view_channel=False)

    # Remove all roles from the user and assign the restricted role
    original_roles = member.roles[1:]
    
    await member.remove_roles(*original_roles, reason="Restricted by bot")
    await member.add_roles(restricted_role, reason="Restricted by bot")

    # Store the restricted user and their previous roles in MongoDB
    restricted_users.update_one(
        {"user_id": member.id, "guild_id": guild.id},
        {"$set": {"roles": [role.id for role in original_roles]}},
        upsert=True
    )
    
    try:
        await interaction.response.send_message(f"{member.mention} has been restricted.", ephemeral=True)
    except nextcord.errors.NotFound as e:
        print(f"Error sending message: {e}")

@bot.slash_command(name="unrestrict", description="Unrestrict a user by restoring their previous roles.")
@commands.has_permissions(manage_roles=True)
async def unrestrict(interaction: nextcord.Interaction, member: nextcord.Member):
    guild = interaction.guild
    restricted_role_name = "Restricted"
    
    # Get the restricted role
    restricted_role = nextcord.utils.get(guild.roles, name=restricted_role_name)
    
    # Check if the user is in the restricted list
    restricted_user = restricted_users.find_one({"user_id": member.id, "guild_id": guild.id})
    
    if restricted_user is None:
        try:
            await interaction.response.send_message(f"{member.mention} is not restricted.", ephemeral=True)
        except nextcord.errors.NotFound as e:
            print(f"Error sending message: {e}")
        return
    
    # Restore original roles
    original_role_ids = restricted_user["roles"]
    original_roles = [guild.get_role(role_id) for role_id in original_role_ids if guild.get_role(role_id)]
    
    # Remove the restricted role
    await member.remove_roles(restricted_role, reason="Unrestricted by bot")
    
    # Add the original roles back
    await member.add_roles(*original_roles, reason="Restored original roles after unrestrict")
    
    # Remove the user from the restricted users database
    restricted_users.delete_one({"user_id": member.id, "guild_id": guild.id})
    
    try:
        await interaction.response.send_message(f"{member.mention} has been unrestricted.", ephemeral=True)
    except nextcord.errors.NotFound as e:
        print(f"Error sending message: {e}")


@bot.slash_command(name="announce", description="Send an announcement to a specified channel with a custom message.")
@commands.has_permissions(administrator=True)
async def announce(interaction: nextcord.Interaction, channel: nextcord.TextChannel, message: str):
    try:
        # Send the announcement to the specified channel
        await channel.send(message)
        await interaction.response.send_message(f"Announcement sent to {channel.mention}.", ephemeral=True)
    except Exception as e:
        print(f"Error sending announcement: {e}")
        await interaction.response.send_message(f"Failed to send announcement: {e}", ephemeral=True)




# stremer settign ans sid config


# Function to generate random unique IDs
def generate_unique_id(collection, field, length=6):
    while True:
        unique_id = ''.join(random.choices('0123456789', k=length))
        if not collection.find_one({field: unique_id}):
            return unique_id

# Command to add a streamer
@bot.slash_command(name="add_streamer", description="Add a new streamer with channel info")
async def add_streamer(interaction: nextcord.Interaction, user: nextcord.Member, channel_name: str, channel_id: str):
    # Defer the response
    await interaction.response.defer()

    # Check if streamer already exists for this user by user_id
    existing_streamer = streamers_collection.find_one({"user_id": user.id})
    if existing_streamer:
        await interaction.followup.send("Streamer already exists. Only one streamer per user.")
        return

    # Generate unique SID and SSP
    sid = f"SID-{generate_unique_id(streamers_collection, 'sid')}"
    ssp = f"SSP-{generate_unique_id(streamers_collection, 'ssp')}"

    # Add to MongoDB
    streamer_data = {
        "user_id": user.id,
        "username": user.name,
        "channel_name": channel_name,
        "status": channel_id,
        "sid": sid,
        "ssp": ssp
    }
    streamers_collection.insert_one(streamer_data)

    # Create SID and SSP roles
    sid_role = await interaction.guild.create_role(name=sid, color=nextcord.Color.red())
    ssp_role = await interaction.guild.create_role(name=ssp, color=nextcord.Color.blue())

    # Assign roles to user
    await user.add_roles(sid_role)

    # Send follow-up message and update embed
    await interaction.followup.send(f"Streamer {user.name} added with SID: {sid} and SSP: {ssp}.")
    await update_embed(interaction.guild)

# Command to edit streamer info by SID
@bot.slash_command(name="edit_streamer", description="Edit a streamer's channel name or status using SID")
async def edit_streamer(interaction: nextcord.Interaction, sid: str, new_channel_name: str = None, new_status: str = None):
    # Defer the response
    await interaction.response.defer()

    streamer = streamers_collection.find_one({"sid": sid})
    if not streamer:
        await interaction.followup.send("Streamer not found.")
        return

    # Update channel name and/or status
    if new_channel_name:
        streamers_collection.update_one({"sid": sid}, {"$set": {"channel_name": new_channel_name}})
    if new_status:
        streamers_collection.update_one({"sid": sid}, {"$set": {"status": new_status}})

    await interaction.followup.send(f"Streamer info updated for SID: {sid}.")
    await update_embed(interaction.guild)

# Command to delete streamer info by SID
@bot.slash_command(name="delete_streamer", description="Delete streamer info by SID")
async def delete_streamer(interaction: nextcord.Interaction, sid: str):
    # Defer the response
    await interaction.response.defer()

    # Fetch streamer by SID
    streamer = streamers_collection.find_one({"sid": sid})
    if not streamer:
        await interaction.followup.send("Streamer not found.")
        return

    # Fetch the user by user_id
    user = interaction.guild.get_member(streamer['user_id'])
    if user:
        sid_role = nextcord.utils.get(interaction.guild.roles, name=streamer['sid'])
        ssp_role = nextcord.utils.get(interaction.guild.roles, name=streamer['ssp'])
        if sid_role:
            await sid_role.delete()
        if ssp_role:
            await ssp_role.delete()

    # Remove streamer from MongoDB
    streamers_collection.delete_one({"sid": sid})

    await interaction.followup.send(f"Streamer with SID: {sid} deleted.")
    await update_embed(interaction.guild)

# Command to check streamer info by mentioning the user
@bot.slash_command(name="check_streamer_info", description="Check a streamer's info by mentioning the user")
async def check_streamer_info(interaction: nextcord.Interaction, user: nextcord.Member):
    # Defer the response
    await interaction.response.defer()

    # Fetch streamer info by user_id
    streamer = streamers_collection.find_one({"user_id": user.id})
    
    if not streamer:
        await interaction.followup.send(f"Streamer info for **{user.display_name}** is not available. No streamer info present.", ephemeral=True)
        return

    # Respond with streamer info in a professional and copyable format
    user_info = (
        f"**Streamer Information for {user.display_name}:**\n"
        f"Channel Name: **{streamer['channel_name']}**\n"
        f"Channel ID: **{streamer['status']}**\n"
        f"Streamer ID (SID): `{streamer['sid']}`\n"
        f"Supporter ID (SSP): `{streamer['ssp']}`"
    )
    
    await interaction.followup.send(user_info, ephemeral=True)


# Function to update the embed message in the info channel
async def update_embed(guild):
    info_channel = nextcord.utils.get(guild.channels, name="stremers-id")
    if not info_channel:
        return

    # Fetch all streamers from DB
    streamers = list(streamers_collection.find({}))
    
    # Build the embed
    embed = nextcord.Embed(title="Streamer Info", color=nextcord.Color.green())
    for streamer in streamers:
        embed.add_field(
            name=f"{streamer['username']} (SID: {streamer['sid']})",
            value=f"Channel: {streamer['channel_name']}\nChannel ID: {streamer['status']}",
            inline=False
        )

    # Update or send the embed message
    async for message in info_channel.history(limit=10):
        if message.author == bot.user and message.embeds:
            await message.edit(embed=embed)
            return
    await info_channel.send(embed=embed)








bot.run(TOKEN)
