import configparser
import os
import sys
import subprocess
import time
import webbrowser


def _import_or_install(module, package=None):
    try:
        return __import__(module)
    except ImportError:
        return _pip_install(package or module)


def _pip_install(package) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


_import_or_install("jwt", "PyJwt")
_import_or_install("requests")


current_dir = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(current_dir, "config.ini")
VERSION = "2.3.0"
GITHUB_REPO = "gorouflex/DuoXPy"
config = configparser.ConfigParser()


def log():
    cls, msg, etb = sys.exc_info()
    fname = os.path.split(etb.tb_frame.f_code.co_filename)[1]
    cname = cls.__name__
    lineno = etb.tb_lineno
    print(f"{fname}: {lineno} --> {cname}: {msg}")


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def welcome() -> None:
    clear()
    print(
        f'''
┌─────────────────────────────────────────────────────┐
│ ╔════════╗               ╔══╗  ╔══╦═══════╗         │
│ ╚╗  ╔═╗  ╠══╗ ╔══╦═══════╣  ╚╗╔╝  ║  ╔═╗  ╠═══╦═══╗ │
│  ║  ║ ║  ║  ║ ║  ║  ╔═╗  ╠═══╗╔═══╣  ╚═╝  ║   ║   ║ │
│  ║  ║ ║  ║  ║ ║  ║  ║ ║  ╠═══╝╚═══╣  ╔════╬═══╗   ║ │
│ ╔╝  ╚═╝  ║  ╚═╝  ║  ╚═╝  ║  ╔╝╚╗  ║  ║    ║       ║ │
│ ╚════════╩═══════╩═══════╩══╝  ╚══╩══╝    ╚═══════╝ │
└─────────────────────────────────────────────────────┘
            v{VERSION} for CLI - by GorouFlex
'''
    )


def create_config() -> None:
    welcome()
    duolingo_jwt = input("Enter your Duolingo JWT: ")
    lessons = input("Enter the number of lessons: ")
    skip_welcome = input("Skip Welcome? (Y/n): ")
    verbose = input("Enable verbose output? (Y/n): ")
    config["Settings"] = {
        "DUOLINGO_JWT": duolingo_jwt,
        "LESSONS": lessons,
        "SKIP_WELCOME": skip_welcome,
        "VERBOSE": verbose,
    }
    write_config()


def check_config_validity() -> None:
    if not os.path.isfile(CONFIG_FILE) or os.stat(CONFIG_FILE).st_size == 0:
        create_config()
        return
    config.read(CONFIG_FILE)
    if (
        not config.has_section("Settings")
        or not config.has_option("Settings", "DUOLINGO_JWT")
        or not config.has_option("Settings", "LESSONS")
        or not config.has_option("Settings", "SKIP_WELCOME")
        or not config.has_option("Settings", "VERBOSE")
    ):
        create_config()


def read_config() -> configparser.SectionProxy:
    config.read(CONFIG_FILE)
    return config["Settings"]


def write_config() -> None:
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)


def update_settings() -> None:
    while True:
        welcome()
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
        match choice:
            case '1':
                config["Settings"]["DUOLINGO_JWT"] = (
                    input(
                        f"Enter your Duolingo JWT [{config['Settings']['DUOLINGO_JWT']}]: "
                    )
                    or config["Settings"]["DUOLINGO_JWT"]
                )
            case '2':
                config["Settings"]["LESSONS"] = (
                    input(
                        f"Enter the number of lessons [{config['Settings']['LESSONS']}]: "
                    )
                    or config["Settings"]["LESSONS"]
                )
            case '3':
                config["Settings"]["SKIP_WELCOME"] = (
                    input(
                        f"Skip Welcome? (Y/n) [{config['Settings']['SKIP_WELCOME']}]: "
                    )
                    or config["Settings"]["SKIP_WELCOME"]
                )
            case '4':
                config["Settings"]["VERBOSE"] = (
                    input(
                        f"Enable verbose output? (Y/n) [{config['Settings']['VERBOSE']}]: "
                    )
                    or config["Settings"]["VERBOSE"]
                )
            case 'b':
                break
            case _:
                print("Invalid option. Please try again.")
                input("Press Enter to continue.")
        write_config()


def decode_jwt(json_web_token: str) -> dict[str, int]:
    options: dict[str, bool] = {
        "verify_signature": False,
        "verify_exp": True,
    }
    try:
        payload = jwt.decode(json_web_token, options=options)
    except jwt.ExpiredSignatureError:
        raise SystemExit("Token has expired, please log in again.")
    except jwt.InvalidTokenError:
        raise SystemExit("Invalid token. Could not verify the token signature.")
    return payload


def _make_request(method: str, url: str, *, headers: dict = None, json: dict = None):
    match method:
        case "GET":
            response = requests.get(url, headers=headers)
        case "POST":
            response = requests.post(url, headers=headers, json=json)
        case "PUT":
            response = requests.put(url, headers=headers, json=json)
        case _:
            raise ValueError(f"Invalid method: {method}")
    data = response.json()
    code = response.status_code
    return code, data


def get_latest_ver() -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    status, data = _make_request(
        "GET",
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        headers=headers,
    )
    if status == 200:
        return data["tag_name"]
    else:
        raise LookupError("Failed to fetch the latest version on GitHub")


def check_updates() -> None:
    LOCAL_VERSION = VERSION
    max_retries = 10
    skip_update_check = False
    for i in range(max_retries):
        try:
            latest_version = get_latest_ver()
        except:
            if i < max_retries - 1:
                print(
                    f"Failed to fetch latest version. Retrying {i+1}/{max_retries}..."
                )
                time.sleep(5)
            else:
                welcome()
                print("Failed to fetch latest version")
                result = (
                    input("Do you want to skip the check for updates? (Y/n): ")
                    .lower()
                    .strip()
                )
                if result == 'y':
                    skip_update_check = True
                else:
                    print("Quitting...")
                    raise SystemExit
        else: # on success
            break
    if not skip_update_check:
        if LOCAL_VERSION < latest_version:
            welcome()
            print(f"New version available: {latest_version}. Updating the script...")
            updater()
            raise SystemExit
        elif LOCAL_VERSION > latest_version:
            welcome()
            print("Welcome to the DuoXPy Beta Program")
            print(
                "This beta build may not work as expected and is only for testing purposes!"
            )
            result = input("Do you want to continue (Y/n): ").lower().strip()
            if result != 'y':
                print("Quitting...")
                raise SystemExit


def updater() -> None:
    latest_url = (
        f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/CLI/DuoXPy-CLI.py"
    )
    response = requests.get(latest_url)
    with open(__file__, 'wb') as f:
        f.write(response.content)
    print("Script updated successfully.")
    input("Press Enter to restart the script")
    raise SystemExit


def switch_to_gui() -> None:
    latest_url = (
        f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/GUI/DuoXPy-GUI.py"
    )
    response = requests.get(latest_url)
    with open(__file__, 'wb') as f:
        f.write(response.content)
    print("Switched to GUI edition successfully.")
    os.remove(CONFIG_FILE)
    input("Press Enter to restart")
    raise SystemExit


def about() -> None:
    options = {
        '1': lambda: webbrowser.open("https://www.github.com/gorouflex/DuoXPy"),
        '2': switch_to_gui,
        'b': "break",
    }
    while True:
        welcome()
        print("About DuoXPy CLI Edition")
        print("The New Hope Update (2NSNH2024)")
        print('-' * 28)
        print("Maintainer: GorouFlex\nCLI: GorouFlex")
        print('-' * 28)
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


def run() -> None:
    welcome()
    config = read_config()
    duolingo_jwt = config["DUOLINGO_JWT"]
    lessons = int(config["LESSONS"])
    skip_welcome = config["SKIP_WELCOME"]
    verbose = config["VERBOSE"]
    print(
        f"Current configuration:\nLessons: {lessons}, Skip Welcome: {skip_welcome}, Verbose: {verbose}"
    )
    print()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {duolingo_jwt}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    }
    try:
        sub: int = decode_jwt(duolingo_jwt)["sub"]
        fields: str = "?fields=" + ','.join(
            ["fromLanguage", "learningLanguage", "streak", "name"]
        )
        user_info_url: str = f"https://www.duolingo.com/2017-06-30/users/{sub}" + fields
        status, user_info = _make_request("GET", user_info_url, headers=headers)
        username: str = user_info["name"]
        streak: int = user_info["streak"]
        fromLanguage: str = user_info["fromLanguage"]
        learningLanguage: str = user_info["learningLanguage"]
        print(f"Logged in as: {username} ({streak} 🔥)")
        print(f"From (language): {fromLanguage}")
        print(f"Learning (language): {learningLanguage}")
        print()
        xp: int = 0

        def progress_bar(completed, total, bar_length=50, xp_gain=None):
            progress = completed / total
            arrow = '-' * int(round(progress * bar_length) - 1) + '>'
            spaces = ' ' * (bar_length - len(arrow))
            percent_complete = int(round(progress * 100))
            if xp_gain is not None:
                print(
                    f"[{completed}] - {xp_gain} XP [{arrow + spaces}] {percent_complete}%"
                )
            else:
                print(f"[{arrow + spaces}] {percent_complete}%", end='\r')

        for i in range(lessons):
            try:
                session_payload = {
                    "challengeTypes": [
                        "assist",
                        "characterIntro",
                        "characterMatch",
                        "characterPuzzle",
                        "characterSelect",
                        "characterTrace",
                        "characterWrite",
                        "completeReverseTranslation",
                        "definition",
                        "dialogue",
                        "extendedMatch",
                        "extendedListenMatch",
                        "form",
                        "freeResponse",
                        "gapFill",
                        "judge",
                        "listen",
                        "listenComplete",
                        "listenMatch",
                        "match",
                        "name",
                        "listenComprehension",
                        "listenIsolation",
                        "listenSpeak",
                        "listenTap",
                        "orderTapComplete",
                        "partialListen",
                        "partialReverseTranslate",
                        "patternTapComplete",
                        "radioBinary",
                        "radioImageSelect",
                        "radioListenMatch",
                        "radioListenRecognize",
                        "radioSelect",
                        "readComprehension",
                        "reverseAssist",
                        "sameDifferent",
                        "select",
                        "selectPronunciation",
                        "selectTranscription",
                        "svgPuzzle",
                        "syllableTap",
                        "syllableListenTap",
                        "speak",
                        "tapCloze",
                        "tapClozeTable",
                        "tapComplete",
                        "tapCompleteTable",
                        "tapDescribe",
                        "translate",
                        "transliterate",
                        "transliterationAssist",
                        "typeCloze",
                        "typeClozeTable",
                        "typeComplete",
                        "typeCompleteTable",
                        "writeComprehension",
                    ],
                    "fromLanguage": fromLanguage,
                    "isFinalLevel": False,
                    "isV2": True,
                    "juicy": True,
                    "learningLanguage": learningLanguage,
                    "smartTipsVersion": 2,
                    "type": "GLOBAL_PRACTICE",
                }
                session_url = "https://www.duolingo.com/2017-06-30/sessions"
                status, session = _make_request(
                    "POST", session_url, headers=headers, json=session_payload
                )
                update_payload = {
                    **session,
                    "heartsLeft": 0,
                    "startTime": (time.time() - 60),
                    "enableBonusPoints": False,
                    "endTime": time.time(),
                    "failed": False,
                    "maxInLessonStreak": 9,
                    "shouldLearnThings": True,
                }
                update_url = (
                    f"https://www.duolingo.com/2017-06-30/sessions/{session['id']}"
                )
                status, response = _make_request(
                    "PUT", update_url, headers=headers, json=update_payload
                )
                z = response["xpGain"]
                xp += z
                if verbose == 'y':
                    progress_bar(i + 1, lessons, xp_gain=z)
                else:
                    progress_bar(i + 1, lessons)
            except Exception as e:
                print(f"An error occurred during lesson {i+1}: {e}")
                log()
        if verbose != 'y':
            print()
        print()
        print('🎉', f"You won {xp} XP")
        input("Press Enter to continue.")
    except Exception as error:
        print('❌', "Something went wrong")
        print(str(error))
        log()
        input("Press Enter to continue.")


def main() -> None:
    check_updates()
    check_config_validity()
    if config.get("Settings", "SKIP_WELCOME", fallback='n').lower().strip() == 'y':
        run()
    else:
        while True:
            welcome()
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
