import os
import json
import base64
import configparser
import time
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error
import webbrowser

current_dir = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(current_dir, 'config.ini')
VERSION = '2.4.0'
GITHUB_REPO = 'gorouflex/DuoXPy' 
config = configparser.ConfigParser()

def clear():
    os.system("cls" if os.name == "nt" else "clear")
    print(r"""  ___          __  _____      
 |   \ _  _ ___\ \/ / _ \_  _ 
 | |) | || / _ \>  <|  _/ || |
 |___/ \_,_\___/_/\_\_|  \_, |
                         |__/ """)
    print(f"Version {VERSION} by GorouFlex - CLI Edition")
    print()

def create_config():
    clear()
    duolingo_jwt = input("Enter your Duolingo JWT: ")
    lessons = input("Enter the number of lessons: ")
    skip_welcome = input("Skip Welcome? (y/n): ")
    verbose = input("Enable verbose output? (y/n): ")
    config['Settings'] = {
        'DUOLINGO_JWT': duolingo_jwt,
        'LESSONS': lessons,
        'SKIP_WELCOME': skip_welcome,
        'VERBOSE': verbose
    }
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def check_config_integrity():
    if not os.path.isfile(CONFIG_FILE) or os.stat(CONFIG_FILE).st_size == 0:
        create_config()
        return
    config.read(CONFIG_FILE)
    if not config.has_section('Settings') or not config.has_option('Settings', 'DUOLINGO_JWT') or not config.has_option('Settings', 'LESSONS') or not config.has_option('Settings', 'SKIP_WELCOME') or not config.has_option('Settings', 'VERBOSE'):
        create_config()

def read_config():
    config.read(CONFIG_FILE)
    return config['Settings']

def update_settings():    
    while True:
        clear()
        print("Settings:")
        print()
        print("1. Duolingo JWT")
        print("2. Lessons")
        print("3. Skip Welcome")
        print("4. Verbose Output")
        print()
        print("B. Back")
        print()
        choice = input("Option: ").lower().strip()
        print()
        if choice == '1':
            config['Settings']['DUOLINGO_JWT'] = input(f"Enter your Duolingo JWT [{config['Settings']['DUOLINGO_JWT']}]: ") or config['Settings']['DUOLINGO_JWT']
        elif choice == '2':
            config['Settings']['LESSONS'] = input(f"Enter the number of lessons [{config['Settings']['LESSONS']}]: ") or config['Settings']['LESSONS']
        elif choice == '3':
            config['Settings']['SKIP_WELCOME'] = input(f"Skip Welcome? (y/n) [{config['Settings']['SKIP_WELCOME']}]: ") or config['Settings']['SKIP_WELCOME']
        elif choice == '4':
            config['Settings']['VERBOSE'] = input(f"Enable verbose output? (y/n) [{config['Settings']['VERBOSE']}]: ") or config['Settings']['VERBOSE']
        elif choice == 'b':
            break
        else:
            print("Invalid option. Please try again.")
            input("Press Enter to continue.")
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

def decode_jwt(jwt):
    _, payload, _ = jwt.split('.')
    decoded = base64.urlsafe_b64decode(payload + "==")
    return json.loads(decoded)

def http_request(method, url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    with urllib.request.urlopen(req) as response:
        return response.getcode(), response.read().decode('utf-8')

def get_latest_ver():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    status, data = http_request("GET", f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", headers)
    if status == 200:
        release_info = json.loads(data)
        return release_info['tag_name']
    else:
        raise Exception("Failed to fetch the latest version from GitHub")

def check_updates():
    LOCAL_VERSION = VERSION
    max_retries = 10
    skip_update_check = False
    for i in range(max_retries):
        try:
            latest_version = get_latest_ver()
            break
        except:
            if i < max_retries - 1:
                print(f"Failed to fetch latest version. Retrying {i+1}/{max_retries}...")
                time.sleep(5)
            else:
                clear()
                print("Failed to fetch latest version")
                result = input("Do you want to skip the check for updates? (y/n): ").lower().strip()
                if result == "y":
                    skip_update_check = True
                else:
                    print("Quitting...")
                    raise SystemExit
    if not skip_update_check:
        if LOCAL_VERSION < latest_version:
            clear()
            print(f"New version available: {latest_version}. Updating the script...")
            updater()
            raise SystemExit
        elif LOCAL_VERSION > latest_version:
            clear()
            print("Welcome to the DuoXPy Beta Program")
            print("This beta build may not work as expected and is only for testing purposes!")
            result = input("Do you want to continue (y/n): ").lower().strip()
            if result != "y":
                print("Quitting...")
                raise SystemExit

def updater():
    latest_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/CLI/DuoXPy-CLI.py"
    response = urllib.request.urlopen(latest_url)
    data = response.read().decode('utf-8')
    with open(__file__, 'w', encoding='utf-8') as f:
        f.write(data)
    print("Script updated successfully.")
    input("Press Enter to restart the script")
    raise SystemExit

def switch_to_gui():
    latest_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/GUI/DuoXPy-GUI.py"
    response = urllib.request.urlopen(latest_url)
    data = response.read().decode('utf-8')
    with open(__file__, 'w', encoding='utf-8') as f:
        f.write(data)
    print("Switched to GUI edition successfully.")
    os.remove(CONFIG_FILE)
    input("Press Enter to restart")
    raise SystemExit

def about():
    options = {
        "1": lambda: webbrowser.open("https://www.github.com/gorouflex/DuoXPy"),
        "2": switch_to_gui,
        "b": "break",
    }
    while True:
        clear()
        print("About DuoXPy CLI Edition")
        print("The New Hope Update (2NSNH2024)")
        print("----------------------------")
        print("Maintainer: GorouFlex\nCLI: GorouFlex")
        print("----------------------------")
        print("\n1. Open GitHub repo")
        print("2. Switch to GUI Edition")
        print("\nB. Back\n")
        choice = input("Option: ").lower().strip()
        action = options.get(choice, None)
        if action is None:
            print("Invalid option.")
            input("Press Enter to continue...")
        elif action == "break":
            break
        else:
            action()

def run():
    clear()
    config = read_config()
    duolingo_jwt = config['DUOLINGO_JWT']
    lessons = int(config['LESSONS'])
    skip_welcome = config['SKIP_WELCOME']
    verbose = config['VERBOSE']
    print(f"Current configuration:\nLessons: {lessons}, Skip Welcome: {skip_welcome}, Verbose: {verbose}")
    print()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {duolingo_jwt}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    try:
        sub = decode_jwt(duolingo_jwt)['sub']
        user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
        status, user_info_data = http_request("GET", user_info_url, headers)
        user_info = json.loads(user_info_data)
        fromLanguage = user_info['fromLanguage']
        learningLanguage = user_info['learningLanguage']
        print(f"From (language): {fromLanguage}")
        print(f"Learning (language): {learningLanguage}")
        print()
        xp = 0

        def progress_bar(completed, total, bar_length=50, xp_gain=None):
            progress = completed / total
            arrow = '-' * int(round(progress * bar_length) - 1) + '>'
            spaces = ' ' * (bar_length - len(arrow))
            percent_complete = int(round(progress * 100))
            if xp_gain is not None:
                print(f'[{completed}] - {xp_gain} XP [{arrow + spaces}] {percent_complete}%')
            else:
                print(f'[{arrow + spaces}] {percent_complete}%', end='\r')

        for i in range(lessons):
            try:
                session_payload = json.dumps({
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
                })
                session_url = "https://www.duolingo.com/2017-06-30/sessions"
                status, session_data = http_request("POST", session_url, headers, session_payload.encode())
                session = json.loads(session_data)
                update_payload = json.dumps({
                    **session,
                    "heartsLeft": 0,
                    "startTime": (datetime.now().timestamp() - 60),
                    "enableBonusPoints": False,
                    "endTime": datetime.now().timestamp(),
                    "failed": False,
                    "maxInLessonStreak": 9,
                    "shouldLearnThings": True
                })
                update_url = f"https://www.duolingo.com/2017-06-30/sessions/{session['id']}"
                status, response_data = http_request("PUT", update_url, headers, update_payload.encode())
                response = json.loads(response_data)
                xp += response['xpGain']
                z = response['xpGain']
                if verbose == 'y':
                    progress_bar(i + 1, lessons, xp_gain=z)
                else:
                    progress_bar(i + 1, lessons)
            except Exception as e:
                print(f"An error occurred during lesson {i+1}: {e}")                           
        if verbose != 'y':
            print() 
        print()
        print(f"🎉 You won {xp} XP")
        input("Press Enter to continue.")
    except Exception as error:
        print("❌ Something went wrong")
        print(str(error))
        input("Press Enter to continue.")

def main():
    check_updates()
    check_config_integrity()
    if config.get('Settings', 'SKIP_WELCOME', fallback='n').lower().strip() == 'y':
        run()
    else:  
        while True:
            clear()
            print("1. Start DuoXPy")
            print("2. Settings")
            print()
            print("A. About")
            print("E. Exit")
            print()
            choice = input("Option: ")
            if choice == '1':
                run()
            elif choice == '2':
                update_settings()
            elif choice.lower() == 'a':
                about()
            elif choice.lower() == 'e':
                break
            else:
                print("Invalid choice. Please try again.")
                input("Press Enter to continue.")

if __name__ == "__main__":
    main()
