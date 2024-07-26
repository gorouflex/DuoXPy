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
bot = commands.Bot(command_prefix='/', intents=intents)
log_channel_id = 123
streak_channel_id = 123
bot_token = 'token_here'

def decode_jwt(jwt):
    try:
        parts = jwt.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        _, payload, _ = parts
        decoded = base64.urlsafe_b64decode(payload + "==")
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None

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
    streak_saver_task.start()

@bot.tree.command(name="login", description="Save your Duolingo JWT token")
@app_commands.describe(jwt_token="Your Duolingo JWT token", account_name="Name of the account")
async def login(interaction: discord.Interaction, jwt_token: str, account_name: str):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id not in accounts:
        accounts[user_id] = {"selected_account": account_name, "accounts": {}}
    
    accounts[user_id]["accounts"][account_name] = {
        "jwt_token": jwt_token,
        "streaksaver": False,
        "duolingo_profile": ""
    }
    save_accounts(accounts)
    await interaction.response.send_message("Your JWT token has been saved!", ephemeral=True)

@bot.tree.command(name="logout", description="Remove your Duolingo JWT token")
@app_commands.describe(account_name="Name of the account to remove")
async def logout(interaction: discord.Interaction, account_name: str):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id in accounts and account_name in accounts[user_id]["accounts"]:
        del accounts[user_id]["accounts"][account_name]
        if accounts[user_id]["selected_account"] == account_name:
            accounts[user_id]["selected_account"] = next(iter(accounts[user_id]["accounts"]), None)
        save_accounts(accounts)
        await interaction.response.send_message("Your account has been removed.", ephemeral=True)
    else:
        await interaction.response.send_message("Account not found.", ephemeral=True)

@bot.tree.command(name="info", description="Show user account information")
async def info(interaction: discord.Interaction):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id in accounts:
        selected_account = accounts[user_id].get("selected_account", "None")
        if selected_account != "None":
            user_info = accounts[user_id]["accounts"][selected_account]
            embed = discord.Embed(
                title="User Information",
                description=f"**Selected Account:** {selected_account}\n\n**JWT Token:** {user_info['jwt_token']}\n**Streak Saver:** {user_info['streaksaver']}\n**Duolingo Profile:** {user_info['duolingo_profile']}",
                color=0x90EE90
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("No selected account. Please select an account using /selectaccount.", ephemeral=True)
    else:
        await interaction.response.send_message("No accounts found. Please log in first using /login.", ephemeral=True)

class SelectAccount(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        accounts = load_accounts()
        self.accounts = accounts.get(user_id, {}).get("accounts", {})
        options = [discord.SelectOption(label=account_name, value=account_name) for account_name in self.accounts.keys()]
        
        if options:
            select = discord.ui.Select(placeholder="Select an account", options=options, custom_id="select_account")
            select.callback = self.select_account_callback
            self.add_item(select)

    async def select_account_callback(self, interaction: discord.Interaction):
        selected_account = interaction.data['values'][0]
        accounts = load_accounts()
        accounts[self.user_id]["selected_account"] = selected_account
        save_accounts(accounts)
        await interaction.response.send_message(f"Selected account: {selected_account}", ephemeral=True)

@bot.tree.command(name="selectaccount", description="Select an account")
async def select_account(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = SelectAccount(user_id)
    
    if view.children:
        await interaction.response.send_message("Select an account from the dropdown:", view=view, ephemeral=True)
    else:
        await interaction.response.send_message("No accounts available to select.", ephemeral=True)

@bot.tree.command(name="listaccount", description="List all added accounts")
async def list_account(interaction: discord.Interaction):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id in accounts:
        user_accounts = accounts[user_id]["accounts"]
        selected_account = accounts[user_id].get("selected_account", "None")
        
        if user_accounts:
            account_list = "\n".join([f"- {acc}" for acc in user_accounts.keys()])
            embed = discord.Embed(
                title="List of Accounts",
                description=f"**Current Selected Account:** {selected_account}\n\n**Accounts:**\n{account_list}",
                color=0x90EE90  # Light green color
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("You have no accounts added. Please log in first using /login.", ephemeral=True)
    else:
        await interaction.response.send_message("No accounts found. Please log in first using /login.", ephemeral=True)

@bot.tree.command(name="about", description="About DuoXPy Discord Bot Edition")
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="About DuoXPy Discord Bot Edition",
        description=(
            " Version 2.4.0 Beta 3\n"
            "- Made by Chromeyc and GorouFlex\n"
            "- Source code: [GitHub](https://github.com/gorouflex/DuoXPy/)"
        ),
        color=0x90EE90
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def process_duolingo(interaction: discord.Interaction, lessons: int):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id not in accounts or not accounts[user_id].get("selected_account"):
        await interaction.followup.send("You need to log in first using /login.", ephemeral=True)
        return
    
    account_name = accounts[user_id]["selected_account"]
    jwt_token = accounts[user_id]["accounts"][account_name]["jwt_token"]
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

            if interaction.guild:
                channel = bot.get_channel(log_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="Duolingo XP Update",
                        description=f"{interaction.user.mention} has been awarded {xp} XP!",
                        color=0x90EE90
                    )
                    await channel.send(embed=embed)
                await interaction.followup.send(f"Done, please check <#{log_channel_id}>", ephemeral=True)
            else:
                embed = discord.Embed(
                    title="Duolingo XP Update",
                    description=f"You won {xp} XP!",
                    color=0x90EE90
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
        color=0x90EE90
    )
    embed.add_field(name="Paypal", value="[Donate Here](https://www.paypal.me/tamkohoatdong)", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="streaksaver", description="Toggle the streak saver feature")
@app_commands.describe(enable="Enable or disable streak saver", account_name="Name of the account")
async def streaksaver(interaction: discord.Interaction, enable: bool, account_name: str):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    if user_id in accounts and account_name in accounts[user_id]["accounts"]:
        accounts[user_id]["accounts"][account_name]["streaksaver"] = enable
        save_accounts(accounts)
        status = "enabled" if enable else "disabled"
        await interaction.response.send_message(f"Streak saver for {account_name} has been {status}.", ephemeral=True)
    else:
        await interaction.response.send_message("Account not found.", ephemeral=True)

@bot.tree.command(name="adduser", description="Add or update your Duolingo profile URL")
@app_commands.describe(profile_url="Your Duolingo profile URL", account_name="Name of the account")
async def add_user(interaction: discord.Interaction, profile_url: str, account_name: str):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id in accounts and account_name in accounts[user_id]["accounts"]:
        accounts[user_id]["accounts"][account_name]["duolingo_profile"] = profile_url
        save_accounts(accounts)
        await interaction.response.send_message(f"Your Duolingo profile URL for {account_name} has been updated to: {profile_url}", ephemeral=True)
    else:
        await interaction.response.send_message("Account not found.", ephemeral=True)

@bot.tree.command(name="finduser", description="Find a user's Duolingo profile URL")
@app_commands.describe(user="The user to find")
async def find_user(interaction: discord.Interaction, user: discord.User):
    accounts = load_accounts()
    user_id = str(user.id)
    embed = discord.Embed(
        title=f"{user.name}'s Duolingo profiles",
        color=0x90EE90
    )
    
    if user_id in accounts:
        account_data = accounts[user_id]["accounts"]
        has_profiles = False
        for account_name, data in account_data.items():
            duolingo_profile = data.get("duolingo_profile", None)
            if duolingo_profile:
                embed.add_field(name=account_name, value=duolingo_profile, inline=False)
                has_profiles = True
        
        if not has_profiles:
            embed.description = "Nothing"
    else:
        embed.description = "Account not found. They might not have logged in or provided a profile URL."
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tasks.loop(hours=24)
async def streak_saver_task():
    now = datetime.now()
    accounts = load_accounts()
    async with aiohttp.ClientSession() as session:
        for user_id, user_data in accounts.items():
            for account_name, data in user_data["accounts"].items():
                if data.get("jwt_token") and data.get("streaksaver"):
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
                        channel = bot.get_channel(log_channel_id)
                        embed = discord.Embed(
                            title="Duolingo XP Update",
                            description=f"<@{user_id}> has been awarded {xp} XP on {account_name}!",
                            color=0x90EE90
                        )
                        if channel:
                            await channel.send(embed=embed)
                    except Exception as error:
                        print(f"Error processing user {user_id} account {account_name}: {error}")

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
    if interaction.guild is None:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if not any(role.permissions.administrator for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Test streak saver in progress...", ephemeral=True)

    accounts = load_accounts()
    async with aiohttp.ClientSession() as session:
        for user_id, user_data in accounts.items():
            for account_name, data in user_data["accounts"].items():
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
                        channel = bot.get_channel(log_channel_id)
                        embed = discord.Embed(
                            title="Duolingo XP Update",
                            description=f"<@{user_id}> has been awarded {xp} XP on {account_name}!",
                            color=0x90EE90
                        )
                        if channel:
                            await channel.send(embed=embed)
                    except Exception as error:
                        print(f"Error processing user {user_id} account {account_name}: {error}")

    await interaction.followup.send("Test streak saver completed.", ephemeral=True)

bot.run(bot_token)
