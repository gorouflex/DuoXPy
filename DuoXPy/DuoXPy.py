import os
import json
import base64
import configparser
import time
from datetime import datetime
import http.client
import urllib.parse
import webbrowser

current_dir = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(current_dir, 'config.ini')
VERSION = '2.0.0'
GITHUB_REPO = 'gorouflex/DuoXPy' 
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

def clear():
    os.system("cls" if os.name == "nt" else "clear")
    print(r"""  ___          __  _____      
 |   \ _  _ ___\ \/ / _ \_  _ 
 | |) | || / _ \>  <|  _/ || |
 |___/ \_,_\___/_/\_\_|  \_, |
                         |__/ """)
    print(f"Version {VERSION}")
    print()

def create_config():
    clear()
    print("Configuration file not found or empty. Please enter the following details:")
    print()
    duolingo_jwt = input("Enter your Duolingo JWT: ")
    lessons = input("Enter the number of lessons: ")
    timer_interval = input("Enter the timer interval (e.g., 10s for 10 seconds, 5m for 5 minutes): ")
    skip_welcome = input("Skip Welcome? (y/n): ")
    config['Settings'] = {
        'DUOLINGO_JWT': duolingo_jwt,
        'LESSONS': lessons,
        'TIMER_INTERVAL': timer_interval,
        'SKIP_WELCOME': skip_welcome
    }

    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def read_config():
    return config['Settings']

def update_settings():    
    clear()
    print("Press Enter and leave nothing if nothing changes")
    print()
    duolingo_jwt = input(f"Enter your Duolingo JWT [{config['Settings']['DUOLINGO_JWT']}]: ") or config['Settings']['DUOLINGO_JWT']
    lessons = input(f"Enter the number of lessons [{config['Settings']['LESSONS']}]: ") or config['Settings']['LESSONS']
    timer_interval = input(f"Enter the timer interval [{config['Settings']['TIMER_INTERVAL']}]: ") or config['Settings']['TIMER_INTERVAL']
    skip_welcome = input(f"Skip Welcome? [{config['Settings']['SKIP_WELCOME']}]: ") or config['Settings']['SKIP_WELCOME']
    
    config['Settings']['DUOLINGO_JWT'] = duolingo_jwt
    config['Settings']['LESSONS'] = lessons
    config['Settings']['TIMER_INTERVAL'] = timer_interval
    config['Settings']['SKIP_WELCOME'] = skip_welcome

    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def parse_timer(timer_str):
    if timer_str[-1] == 's':
        return int(timer_str[:-1])
    elif timer_str[-1] == 'm':
        return int(timer_str[:-1]) * 60
    else:
        raise ValueError("Invalid timer format. Use 'Xs' for seconds or 'Xm' for minutes.")

def decode_jwt(jwt):
    _, payload, _ = jwt.split('.')
    decoded = base64.urlsafe_b64decode(payload + "==")
    return json.loads(decoded)

def http_request(method, url, headers=None, body=None):
    parsed_url = urllib.parse.urlparse(url)
    conn = http.client.HTTPSConnection(parsed_url.netloc)
    conn.request(method, parsed_url.path + ('?' + parsed_url.query if parsed_url.query else ''), body, headers)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    conn.close()
    return response.status, data

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
            print(f"New version available: {latest_version}. Please update the script.")
            raise SystemExit
        elif LOCAL_VERSION > latest_version:
            clear()
            print("Welcome to the DuoXPy Beta Program")
            print("This beta build may not work as expected and is only for testing purposes!")
            result = input("Do you want to continue (y/n): ").lower().strip()
            if result != "y":
                print("Quitting...")
                raise SystemExit

def about():
    options = {
        "1": lambda: webbrowser.open("https://www.github.com/AppleOSX/UXTU4Unix"),
        "b": "break",
    }
    while True:
        clear()
        print("About DuoXPy")
        print("The New Hope Update (2NewHopeL2T)")
        print("----------------------------")
        print("Maintainer: GorouFlex\nCLI: GorouFlex")
        print("----------------------------")
        print("\nB. Back")
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
    timer_interval = parse_timer(config['TIMER_INTERVAL'])
    skip_welcome = config['SKIP_WELCOME']
    print(f"Current configuration:\nLessons: {lessons}, Timer Interval: {config['TIMER_INTERVAL']}, Skip Welcome: {skip_welcome}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {duolingo_jwt}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    try:
        sub = decode_jwt(duolingo_jwt)['sub']
        user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
        status, user_info_data = http_request("GET", user_info_url, headers)
        if status == 500:
            print("❌ SkillID error. Server returned status code 500.")
            pass
        user_info = json.loads(user_info_data)
        fromLanguage = user_info['fromLanguage']
        learningLanguage = user_info['learningLanguage']
        xp = 0
        for _ in range(lessons):
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
            status, session_data = http_request("POST", session_url, headers, session_payload)
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
            status, response_data = http_request("PUT", update_url, headers, update_payload)
            response = json.loads(response_data)
            xp += response['xpGain']
            z = response['xpGain']
            print(f"[{_+1}] - {z} XP")
            time.sleep(timer_interval)
                           

        print(f"🎉 You won {xp} XP")
        input("Press Enter to continue.")
    except Exception as error:
        print("❌ Something went wrong")
        print(str(error))
        input("Press Enter to continue.")

def main():
    check_updates()
    if not os.path.exists(CONFIG_FILE) or os.stat(CONFIG_FILE).st_size == 0:
        create_config()
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
