# // MAKE SURE TO CREATE A accounts.json file 
# // If still errors add a { } in the accounts.json file
# // Made by Chromeyc and GorouFlex

import os
import json
import base64
import aiohttp
from datetime import datetime
import discord
from discord.ext import commands, tasks
from discord import app_commands

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
log_channel_id = 123  # Do not use string ' '
streak_channel_id = 123  # Do not use string ' '
bot_token = 'insert token here' # use string ' '

def decode_jwt(jwt):
    _, payload, _ = jwt.split('.')
    decoded = base64.urlsafe_b64decode(payload + "==")
    return json.loads(decoded)

def load_accounts():
    if os.path.exists('accounts.json'):
        with open('accounts.json', 'r') as f:
            return json.load(f)
    return {}

def save_accounts(accounts):
    with open('accounts.json', 'w') as f:
        json.dump(accounts, f)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing commands: {e}')
    # Start the streak saver task
    streak_saver_task.start()

@bot.tree.command(name="login", description="Save your Duolingo JWT token")
@app_commands.describe(jwt_token="Your Duolingo JWT token")
async def login(interaction: discord.Interaction, jwt_token: str):
    accounts = load_accounts()
    accounts[str(interaction.user.id)] = {
        "jwt_token": jwt_token,
        "streaksaver": False,
        "duolingo_profile": ""  # Initialize the profile URL as empty
    }
    save_accounts(accounts)
    await interaction.response.send_message("Your JWT token has been saved!", ephemeral=True)

async def process_duolingo(interaction: discord.Interaction, lessons: int):
    accounts = load_accounts()
    user_id = str(interaction.user.id)

    if user_id not in accounts:
        await interaction.followup.send("You need to log in first using /login.", ephemeral=True)
        return

    jwt_token = accounts[user_id]["jwt_token"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        try:
            sub = decode_jwt(jwt_token)['sub']
            user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
            async with session.get(user_info_url, headers=headers) as response:
                user_info = await response.json()
            fromLanguage = user_info['fromLanguage']
            learningLanguage = user_info['learningLanguage']
            xp = 0

            for _ in range(lessons):
                session_payload = {
                    "challengeTypes": [
                        "assist", "characterIntro", "characterMatch", "characterPuzzle",
                        "characterSelect", "characterTrace", "characterWrite",
                        "completeReverseTranslation", "definition", "dialogue",
                        "extendedMatch", "extendedListenMatch", "form", "freeResponse",
                        "gapFill", "judge", "listen", "listenComplete", "listenMatch",
                        "match", "name", "listenComprehension", "listenIsolation",
                        "listenSpeak", "listenTap", "orderTapComplete", "partialListen",
                        "partialReverseTranslate", "patternTapComplete", "radioBinary",
                        "radioImageSelect", "radioListenMatch", "radioListenRecognize",
                        "radioSelect", "readComprehension", "reverseAssist",
                        "sameDifferent", "select", "selectPronunciation",
                        "selectTranscription", "svgPuzzle", "syllableTap",
                        "syllableListenTap", "speak", "tapCloze", "tapClozeTable",
                        "tapComplete", "tapCompleteTable", "tapDescribe", "translate",
                        "transliterate", "transliterationAssist", "typeCloze",
                        "typeClozeTable", "typeComplete", "typeCompleteTable",
                        "writeComprehension"
                    ],
                    "fromLanguage": fromLanguage,
                    "isFinalLevel": False,
                    "isV2": True,
                    "juicy": True,
                    "learningLanguage": learningLanguage,
                    "smartTipsVersion": 2,
                    "type": "GLOBAL_PRACTICE"
                }
                session_url = "https://www.duolingo.com/2017-06-30/sessions"
                async with session.post(session_url, headers=headers, json=session_payload) as response:
                    session_data = await response.json()
                update_payload = {
                    **session_data,
                    "heartsLeft": 0,
                    "startTime": (datetime.now().timestamp() - 60),
                    "enableBonusPoints": False,
                    "endTime": datetime.now().timestamp(),
                    "failed": False,
                    "maxInLessonStreak": 9,
                    "shouldLearnThings": True
                }
                update_url = f"https://www.duolingo.com/2017-06-30/sessions/{session_data['id']}"
                async with session.put(update_url, headers=headers, json=update_payload) as response:
                    update_response = await response.json()
                xp += update_response['xpGain']

            # Send message to channel or DM based on interaction context
            if interaction.guild:
                channel = bot.get_channel(log_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="Duolingo XP Update",
                        description=f"{interaction.user.mention} You has been awarded {xp} XP!",
                        color=0x90EE90  # Light green color
                    )
                    await channel.send(embed=embed)
                await interaction.followup.send(f"Done, please check <#{log_channel_id}>", ephemeral=True)
            else:
                embed = discord.Embed(
                    title="Duolingo XP Update",
                    description=f"You won {xp} XP!",
                    color=0x90EE90  # Light green color
                )
                await interaction.user.send(embed=embed)

        except Exception as error:
            await interaction.followup.send(f"❌ Something went wrong: {str(error)}", ephemeral=True)

@bot.tree.command(name="duolingo", description="Complete Duolingo lessons and gain XP")
@app_commands.describe(lessons="Number of lessons to complete")
async def start_duolingo(interaction: discord.Interaction, lessons: int):
    await interaction.response.send_message("Processing your request, please wait...", ephemeral=True)
    bot.loop.create_task(process_duolingo(interaction, lessons))

@bot.tree.command(name="donate", description="Donate us")
async def donate(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Feel Free To Donate",
        description="We appreciate all your donations",
        color=0x90EE90  # Light green color
    )
    embed.add_field(name="Paypal", value="[Donate Here](https://www.paypal.me/tamkohoatdong)", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="streaksaver", description="Toggle the streak saver feature")
@app_commands.describe(enable="Enable or disable streak saver")
async def streaksaver(interaction: discord.Interaction, enable: bool):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    if user_id in accounts:
        accounts[user_id]["streaksaver"] = enable
    else:
        accounts[user_id] = {
            "jwt_token": "",
            "streaksaver": enable,
            "duolingo_profile": ""  # Initialize the profile URL as empty
        }
    save_accounts(accounts)
    status = "enabled" if enable else "disabled"
    await interaction.response.send_message(f"Streak saver has been {status}.", ephemeral=True)

@bot.tree.command(name="adduser", description="Add or update your Duolingo profile URL")
@app_commands.describe(profile_url="Your Duolingo profile URL")
async def add_user(interaction: discord.Interaction, profile_url: str):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id in accounts:
        accounts[user_id]["duolingo_profile"] = profile_url
        save_accounts(accounts)
        await interaction.response.send_message(f"Your Duolingo profile URL has been updated to: {profile_url}", ephemeral=True)
    else:
        await interaction.response.send_message("You need to log in first using /login before adding your profile URL.", ephemeral=True)

@bot.tree.command(name="finduser", description="Find a user's Duolingo profile URL")
@app_commands.describe(user="The user to find")
async def find_user(interaction: discord.Interaction, user: discord.User):
    accounts = load_accounts()
    user_id = str(user.id)
    if user_id in accounts:
        duolingo_profile = accounts[user_id].get("duolingo_profile", "Not set")
        await interaction.response.send_message(f"{user.mention}'s Duolingo profile: {duolingo_profile}", ephemeral=True)
    else:
        await interaction.response.send_message("User not found. They might not have logged in or provided a profile URL.", ephemeral=True)

@tasks.loop(hours=1)
async def streak_saver_task():
    now = datetime.now()
    # Notify that the streak saver function has run
    channel_status = bot.get_channel(streak_channel_id)
    if channel_status:
        status_embed = discord.Embed(
            title="Streak Saver Task",
            description=f"Streak saver task ran at {now.strftime('%Y-%m-%d %H:%M:%S')}",
            color=0x90EE90
        )
        await channel_status.send(embed=status_embed)

@bot.tree.command(name="teststreaksaver", description="Test streak saver for all logged in accounts")
async def test_streaksaver(interaction: discord.Interaction):
    if not any(role.permissions.administrator for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Test streak saver in progress...", ephemeral=True)

    accounts = load_accounts()
    async with aiohttp.ClientSession() as session:
        for user_id, data in accounts.items():
            if data.get("jwt_token"):
                jwt_token = data["jwt_token"]
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {jwt_token}",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                }
                try:
                    sub = decode_jwt(jwt_token)['sub']
                    user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
                    async with session.get(user_info_url, headers=headers) as response:
                        user_info = await response.json()
                    fromLanguage = user_info['fromLanguage']
                    learningLanguage = user_info['learningLanguage']

                    session_payload = {
                        "challengeTypes": [
                            "assist", "characterIntro", "characterMatch", "characterPuzzle",
                            "characterSelect", "characterTrace", "characterWrite",
                            "completeReverseTranslation", "definition", "dialogue",
                            "extendedMatch", "extendedListenMatch", "form", "freeResponse",
                            "gapFill", "judge", "listen", "listenComplete", "listenMatch",
                            "match", "name", "listenComprehension", "listenIsolation",
                            "listenSpeak", "listenTap", "orderTapComplete", "partialListen",
                            "partialReverseTranslate", "patternTapComplete", "radioBinary",
                            "radioImageSelect", "radioListenMatch", "radioListenRecognize",
                            "radioSelect", "readComprehension", "reverseAssist",
                            "sameDifferent", "select", "selectPronunciation",
                            "selectTranscription", "svgPuzzle", "syllableTap",
                            "syllableListenTap", "speak", "tapCloze", "tapClozeTable",
                            "tapComplete", "tapCompleteTable", "tapDescribe", "translate",
                            "transliterate", "transliterationAssist", "typeCloze",
                            "typeClozeTable", "typeComplete", "typeCompleteTable",
                            "writeComprehension"
                        ],
                        "fromLanguage": fromLanguage,
                        "isFinalLevel": False,
                        "isV2": True,
                        "juicy": True,
                        "learningLanguage": learningLanguage,
                        "smartTipsVersion": 2,
                        "type": "GLOBAL_PRACTICE"
                    }
                    session_url = "https://www.duolingo.com/2017-06-30/sessions"
                    async with session.post(session_url, headers=headers, json=session_payload) as response:
                        session_data = await response.json()
                    update_payload = {
                        **session_data,
                        "heartsLeft": 0,
                        "startTime": (datetime.now().timestamp() - 60),
                        "enableBonusPoints": False,
                        "endTime": datetime.now().timestamp(),
                        "failed": False,
                        "maxInLessonStreak": 9,
                        "shouldLearnThings": True
                    }
                    update_url = f"https://www.duolingo.com/2017-06-30/sessions/{session_data['id']}"
                    async with session.put(update_url, headers=headers, json=update_payload) as response:
                        update_response = await response.json()
                    xp = update_response['xpGain']
                    # Send the result to a specific channel
                    channel = bot.get_channel(log_channel_id)
                    embed = discord.Embed(
                        title="Duolingo XP Update",
                        description=f"<@{user_id}> has been awarded {xp} XP!",
                        color=0x90EE90  # Light green color
                    )
                    if channel:
                        await channel.send(embed=embed)
                except Exception as error:
                    print(f"Error processing user {user_id}: {error}")

    await interaction.followup.send("Test streak saver completed.", ephemeral=True)

bot.run(bot_token)
