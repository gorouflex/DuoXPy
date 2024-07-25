# // MAKE SURE TO CREATE A accounts.json file 
# // If still errors add a { } in the accounts.json file

import os
import json
import base64
import requests
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
from discord import app_commands

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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
        "streaksaver": False
    }
    save_accounts(accounts)
    await interaction.response.send_message("Your JWT token has been saved!", ephemeral=True)

@bot.tree.command(name="duolingo", description="Complete Duolingo lessons and gain XP")
@app_commands.describe(lessons="Number of lessons to complete")
async def start_duolingo(interaction: discord.Interaction, lessons: int):
    await interaction.response.send_message("Processing your request, please wait...", ephemeral=True)
    
    bot.loop.create_task(process_duolingo(interaction, lessons))

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

    try:
        sub = decode_jwt(jwt_token)['sub']
        user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
        user_info = requests.get(user_info_url, headers=headers).json()
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
            session = requests.post(session_url, headers=headers, json=session_payload).json()
            update_payload = {
                **session,
                "heartsLeft": 0,
                "startTime": (datetime.now().timestamp() - 60),
                "enableBonusPoints": False,
                "endTime": datetime.now().timestamp(),
                "failed": False,
                "maxInLessonStreak": 9,
                "shouldLearnThings": True
            }
            update_url = f"https://www.duolingo.com/2017-06-30/sessions/{session['id']}"
            response = requests.put(update_url, headers=headers, json=update_payload).json()
            xp += response['xpGain']
        
        # Send the result to a specific channel
        channel = bot.get_channel(1261239245415120936)
        if channel:
            embed = discord.Embed(
                title="Duolingo XP Update",
                description=f"{interaction.user.mention} You won {xp} XP!",
                color=0x90EE90  # Light green color
            )
            await channel.send(embed=embed)
        else:
            print(f"Channel with ID 1261239245415120936 not found.")
        
    except Exception as error:
        # Send error message to the same channel as interaction
        await interaction.followup.send(f"❌ Something went wrong: {str(error)}")

@bot.tree.command(name="donate", description="Send a donation link")
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
            "streaksaver": enable
        }
    save_accounts(accounts)
    status = "enabled" if enable else "disabled"
    await interaction.response.send_message(f"Streak saver has been {status}.", ephemeral=True)

@tasks.loop(hours=1)
async def streak_saver_task():
    now = datetime.now()
    # Notify that the streak saver function has run
    channel_status = bot.get_channel(1261239177958264854)
    if channel_status:
        status_embed = discord.Embed(
            title="Streak Saver Notification",
            description="The streak saver function has run successfully.",
            color=0x90EE90  # Light green color
        )
        await channel_status.send(embed=status_embed)
    else:
        print(f"Channel with ID 1261239177958264854 not found.")

    # Award XP to users with streak saver enabled
    accounts = load_accounts()
    for user_id, data in accounts.items():
        if data.get("streaksaver"):
            channel = bot.get_channel(1261239245415120936)
            if channel:
                # Process one lesson
                jwt_token = data["jwt_token"]
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {jwt_token}",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                }
                try:
                    sub = decode_jwt(jwt_token)['sub']
                    user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
                    user_info = requests.get(user_info_url, headers=headers).json()
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
                    session = requests.post(session_url, headers=headers, json=session_payload).json()
                    update_payload = {
                        **session,
                        "heartsLeft": 0,
                        "startTime": (datetime.now().timestamp() - 60),
                        "enableBonusPoints": False,
                        "endTime": datetime.now().timestamp(),
                        "failed": False,
                        "maxInLessonStreak": 9,
                        "shouldLearnThings": True
                    }
                    update_url = f"https://www.duolingo.com/2017-06-30/sessions/{session['id']}"
                    response = requests.put(update_url, headers=headers, json=update_payload).json()
                    xp = response['xpGain']

                    embed = discord.Embed(
                        title="Duolingo XP Update",
                        description=f"<@{user_id}> has been awarded {xp} XP for their streak saver!",
                        color=0x90EE90  # Light green color
                    )
                    await channel.send(embed=embed)

                    # Optionally update user's XP in your accounts or another storage mechanism
                    if "xp" in data:
                        data["xp"] += xp
                    else:
                        data["xp"] = xp
                    save_accounts(accounts)

                except Exception as e:
                    # Log or notify about the error
                    print(f"Error processing streak saver for user {user_id}: {e}")

@bot.tree.command(name="teststreaksaver", description="Test streak saver for all logged in accounts")
async def test_streaksaver(interaction: discord.Interaction):
    if not any(role.permissions.administrator for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    accounts = load_accounts()
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
                user_info = requests.get(user_info_url, headers=headers).json()
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
                session = requests.post(session_url, headers=headers, json=session_payload).json()
                update_payload = {
                    **session,
                    "heartsLeft": 0,
                    "startTime": (datetime.now().timestamp() - 60),
                    "enableBonusPoints": False,
                    "endTime": datetime.now().timestamp(),
                    "failed": False,
                    "maxInLessonStreak": 9,
                    "shouldLearnThings": True
                }
                update_url = f"https://www.duolingo.com/2017-06-30/sessions/{session['id']}"
                response = requests.put(update_url, headers=headers, json=update_payload).json()
                xp = response['xpGain']

                # Send the result to a specific channel
                channel = bot.get_channel(1261239245415120936)
                if channel:
                    embed = discord.Embed(
                        title="Duolingo XP Update",
                        description=f"<@{user_id}> has been awarded {xp} XP!",
                        color=0x90EE90  # Light green color
                    )
                    await channel.send(embed=embed)
                else:
                    print(f"Channel with ID 1261239245415120936 not found.")
            except Exception as error:
                # Log or notify about the error
                print(f"Error processing user {user_id}: {error}")

    await interaction.response.send_message("Test streak saver completed.", ephemeral=True)

bot.run('your-bot-token')
