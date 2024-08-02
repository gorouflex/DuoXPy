import os
import json
import base64
import aiohttp
import time
from datetime import datetime
import discord
from discord.ext import commands, tasks
from discord import app_commands

VERSION = "2.4.2"
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)
log_channel_id = 123 # Logs Chanell
streak_channel_id = 123 # Streak Notification Chanell
bot_token = 'Your-Bot-Token-Here' # Bot Token


# Define the file path
SUPERLINKS_FILE = 'superlinks.txt' # Superlink File Directory

# Define the load_superlinks function to read from a file
def load_superlinks():
    try:
        with open(SUPERLINKS_FILE, 'r') as file:
            links = file.readlines()
            links = [link.strip() for link in links if link.strip()]
        return links
    except FileNotFoundError:
        print(f"{SUPERLINKS_FILE} not found")
        return []

# Define the save_superlinks function to write to a file
def save_superlinks(superlinks):
    with open(SUPERLINKS_FILE, 'w') as file:
        for link in superlinks:
            file.write(f"{link}\n")

# Check if the user has Administrator permission
def has_admin_permissions(user):
    return any(role.permissions.administrator for role in user.roles)

def decode_jwt(jwt):
    try:
        parts = jwt.split('.')
        if len(parts) != 3:
            raise ValueError("[LOG] Invalid JWT format")
        _, payload, _ = parts
        decoded = base64.urlsafe_b64decode(payload + "==")
        return json.loads(decoded)
    except Exception as e:
        print(f"[LOG] Error decoding JWT: {e}")
        return None

def load_accounts():
    if os.path.exists('accounts.json'):
        with open('accounts.json', 'r') as f:
            return json.load(f)
    return {}

def save_accounts(accounts):
    with open('accounts.json', 'w') as f:
        json.dump(accounts, f)

async def send_embed_message(channel_id, title, description, color=0x90EE90):
    channel = bot.get_channel(channel_id)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color)
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'[LOG] Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'[LOG] Error syncing commands: {e}')
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
    await interaction.response.send_message(embed=discord.Embed(
        title="[DuoXPy] Login",
        description="✅Your JWT token has been saved!",
        color=0x90EE90
    ), ephemeral=True)

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
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Logout",
            description="Your account has been removed.",
            color=0x90EE90
        ), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Logout",
            description="❌Account not found.",
            color=0x90EE90
        ), ephemeral=True)

@bot.tree.command(name="info", description="Show user account information")
async def info(interaction: discord.Interaction):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id in accounts:
        selected_account = accounts[user_id].get("selected_account", "None")
        if selected_account != "None":
            user_info = accounts[user_id]["accounts"][selected_account]
            embed = discord.Embed(
                title="DuoXPy User Information",
                description=f"**Selected Account:** {selected_account}\n\n**JWT Token:** {user_info['jwt_token']}\n**Streak Saver:** {user_info['streaksaver']}\n**Duolingo Profile:** {user_info['duolingo_profile']}",
                color=0x90EE90
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="[DuoXPy] Info",
                description="❌No selected account. Please select an account using `/selectaccount`.",
                color=0x90EE90
            ), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Info",
            description="❌No accounts found. Please log in first using `/login`.",
            color=0x90EE90
        ), ephemeral=True)

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
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Select Account",
            description=f"Selected account: {selected_account}",
            color=0x90EE90
        ), ephemeral=True)

@bot.tree.command(name="selectaccount", description="Select an account")
async def select_account(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = SelectAccount(user_id)
    
    if view.children:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Select Account",
            description="Select an account:",
            color=0x90EE90
        ), view=view, ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Select Account",
            description="❌No accounts available to select.",
            color=0x90EE90
        ), ephemeral=True)

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
            await interaction.response.send_message(embed=discord.Embed(
                title="[DuoXPy] List Account",
                description="❌You have no accounts added. Please log in first using `/login`.",
                color=0x90EE90
            ), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] List Account",
            description="❌No accounts found. Please log in first using `/login`.",
            color=0x90EE90
        ), ephemeral=True)

## Who change this is a bitch
@bot.tree.command(name="about", description="About DuoXPy Discord Bot Edition")
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="About DuoXPy Discord Bot Edition",
        description=(
            f"Version {VERSION}\n"
            "- Made by [Chromeyc](https://github.com/Chromeyc/) and [GorouFlex](https://github.com/gorouflex/)\n"
            "- Source code: [GitHub](https://github.com/gorouflex/DuoXPy/)"
            "- Website: [Website](https://chromeyc.github.io/Duolingo-XP-Website/)"
        ),
        color=0x90EE90
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def process_duolingo(interaction: discord.Interaction, lessons: int):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id not in accounts or not accounts[user_id].get("selected_account"):
        await interaction.followup.send(embed=discord.Embed(
            title="[DuoXPy] Error",
            description="❌You need to log in first using `/login` or using `/help` for more information",
            color=0xFF0000
        ), ephemeral=True)
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
                        title="DuoXPy status⚡",
                        description=f"{interaction.user.mention} has been awarded {xp} XP on `{account_name}`!🎉",
                        color=0x90EE90
                    )
                    await channel.send(embed=embed)
                await interaction.followup.send(embed=discord.Embed(
                    title="[DuoXPy] Duolingo",
                    description=f"✅Done, please check <#{log_channel_id}>",
                    color=0x90EE90
                ), ephemeral=True)
            else:
                embed = discord.Embed(
                    title="DuoXPy status⚡",
                    description=f"You won {xp} XP!🎉",
                    color=0x90EE90
                )
                await interaction.user.send(embed=embed)

        except Exception as error:
            await interaction.followup.send(embed=discord.Embed(
                title="[DuoXPy] Error",
                description=f"❌ Something went wrong: {str(error)}",
                color=0xFF0000
            ), ephemeral=True)

@bot.tree.command(name="duolingo", description="Complete Duolingo lessons and gain XP")
@app_commands.describe(lessons="Number of lessons to complete")
async def start_duolingo(interaction: discord.Interaction, lessons: int):
    await interaction.response.send_message(embed=discord.Embed(
        title="[DuoXPy] Duolingo",
        description="Processing your request, please wait...",
        color=0x90EE90
    ), ephemeral=True)
    bot.loop.create_task(process_duolingo(interaction, lessons))

@bot.tree.command(name="donate", description="Donate us")
async def donate(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Feel Free To Donate",
        description="❤️We appreciate all your donations",
        color=0x90EE90
    )
    embed.add_field(name="Paypal", value="[Donate Here](https://www.paypal.me/tamkohoatdong) <:6659paypallogo:1266414604636917905>", inline=False)
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
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Streak Saver",
            description=f"🔥Streak saver for `{account_name}` has been set to {status}.",
            color=0x90EE90
        ), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Error",
            description="❌Account not found.",
            color=0xFF0000
        ), ephemeral=True)

@bot.tree.command(name="adduser", description="Add or update your Duolingo profile URL")
@app_commands.describe(profile_url="Your Duolingo profile URL", account_name="Name of the account")
async def add_user(interaction: discord.Interaction, profile_url: str, account_name: str):
    accounts = load_accounts()
    user_id = str(interaction.user.id)
    
    if user_id in accounts and account_name in accounts[user_id]["accounts"]:
        accounts[user_id]["accounts"][account_name]["duolingo_profile"] = profile_url
        save_accounts(accounts)
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Add User",
            description=f"Your Duolingo profile URL for `{account_name}` has been updated to: {profile_url}",
            color=0x90EE90
        ), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Error",
            description="❌Account not found.",
            color=0xFF0000
        ), ephemeral=True)

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
            embed.description = "❌Nothing/Empty❌"
    else:
        embed.description = "❌Account not found. They might not have logged in or provided a profile URL."
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tasks.loop(hours=23)
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
                        await send_embed_message(log_channel_id, "DuoXPy Streak Saver 🔥",
                            f"<@{user_id}> has been awarded {xp} XP on `{account_name}`!", 0xFF9900)
                    except Exception as error:
                        print(f"Error processing user `{user_id}` on account `{account_name}`: {error}")

    await send_embed_message(streak_channel_id, "DuoXPy Streak Saver <:Streak:1266290974275932262>",
        f"Streak saver task ran at {now.strftime('%Y-%m-%d %H:%M:%S')} <:Streak:1266290974275932262>", 0xFF7518)

@bot.tree.command(name="guidetoken", description="Guide on how to use Duolingo JWT token")
async def guide_token(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Guide to Using Duolingo JWT Token",
        description=(
            "To use this bot effectively, follow these steps:\n\n"
            "**1. Obtain JWT Token:**\n"
            "   - Copy the Code in <#1261239187076812821> Then Press Right Click on `duolingo.com` And Press `Inspect` or press `CTRL + SHIFT + I` Then Go To The `Console Tab` And Paste the Code in <#1261239187076812821>\n\n"
            "**2. Save JWT Token:**\n"
            "   - Use the `/login` command with your JWT token to save it in the bot.\n\n"
            "**3. Select Account:**\n"
            "   - Use the `/selectaccount` command to choose the account you want to work with.\n\n"
            "**4. Manage Account:**\n"
            "   - Use `/logout` to remove an account, `/info` to view details, and `/adduser` to update your profile URL.\n\n"
            "**5. Perform Actions:**\n"
            "   - Use `/duolingo` to complete lessons and gain XP, and `/streaksaver` to enable or disable the streak saver feature.\n\n"
            "For more information, use `/help` to see a list of all commands."
        ),
        color=0x90EE90
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="List all available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Available Commands",
        description=(
            "**/login** - Save your Duolingo JWT token\n"
            "**/logout** - Remove your Duolingo JWT token\n"
            "**/info** - Show user account information\n"
            "**/selectaccount** - Select an account\n"
            "**/listaccount** - List all added accounts\n"
            "**/about** - About DuoXPy Discord Bot Edition\n"
            "**/duolingo** - Complete Duolingo lessons and gain XP\n"
            "**/donate** - Donate to support us\n"
            "**/streaksaver** - Toggle the streak saver feature\n"
            "**/adduser** - Add or update your Duolingo profile URL\n"
            "**/finduser** - Find a user's Duolingo profile URL\n"
            "**/guidetoken** - Guide on how to use Duolingo JWT token\n"
            "**/help** - List all available commands"
            "**getsuper** - Get Super Duolingo For Free"
        ),
        color=0x90EE90
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command(name="teststreaksaver", description="Test streak saver for all logged in accounts")
async def test_streaksaver(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Error",
            description="❌You do not have permission to use this command.❌",
            color=0xFF0000
        ), ephemeral=True)
        return

    if not any(role.permissions.administrator for role in interaction.user.roles):
        await interaction.response.send_message(embed=discord.Embed(
            title="[DuoXPy] Error",
            description="❌You do not have permission to use this command.❌",
            color=0xFF0000
        ), ephemeral=True)
        return

    await interaction.response.send_message(embed=discord.Embed(
        title="[DuoXPy] Test Streak Saver",
        description="Test streak saver in progress...🔥",
        color=0x90EE90
    ), ephemeral=True)
    await streak_saver_task() 
    await interaction.followup.send(embed=discord.Embed(
        title="[DuoXPy] Test Streak Saver",
        description="Test streak saver completed. 🔥",
        color=0x90EE90
    ), ephemeral=True)


@bot.tree.command(name='listlinks', description='Lists all superlinks')
async def list_links(interaction: discord.Interaction):
    if not has_admin_permissions(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    superlinks = load_superlinks()
    if superlinks:
        links_list = '\n'.join(superlinks)
        await interaction.response.send_message(f"Superlinks:\n{links_list}")
    else:
        await interaction.response.send_message("No superlinks found.")

@bot.tree.command(name='addlink', description='Adds a new superlink')
async def add_link(interaction: discord.Interaction, link: str):
    if not has_admin_permissions(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    superlinks = load_superlinks()
    if link in superlinks:
        await interaction.response.send_message("This link is already in the list.")
        return

    superlinks.append(link)
    save_superlinks(superlinks)
    await interaction.response.send_message(f"Added new link: {link}")
@bot.tree.command(name='getsuper', description='Gets and removes one working superlink')
async def get_super(interaction: discord.Interaction):
    superlinks = load_superlinks()
    
    if superlinks:
        # Provide the first link in the list
        link = superlinks.pop(0)  # Get and remove the first link
        save_superlinks(superlinks)  # Save the updated list
        await interaction.response.send_message(f"Here is a superlink: {link}")
    else:
        await interaction.response.send_message("No superlinks available.")



# Start the bot
bot.run(bot_token)
