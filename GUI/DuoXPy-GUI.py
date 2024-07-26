import os
import json
import base64
import configparser
import time
from datetime import datetime
import urllib.request
import urllib.error
import webbrowser
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import threading

current_dir = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(current_dir, 'config.ini')
VERSION = '2.4.0'
GITHUB_REPO = 'gorouflex/DuoXPy'
CLI_FILE_PATH = 'CLI/DuoXPy-CLI.py'
config = configparser.ConfigParser()

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.title('Settings')
        self.geometry("325x250")
        self.resizable(False, False)
        
        self.frame = ctk.CTkFrame(master=self)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)

        ctk.CTkLabel(master=self.frame, text="Duolingo JWT:", font=("", 14)).pack(pady=2)
        self.jwt_entry = ctk.CTkEntry(master=self.frame)
        self.jwt_entry.pack(pady=5)

        ctk.CTkLabel(master=self.frame, text="Number of Lessons:", font=("", 14)).pack(pady=2)
        self.lessons_entry = ctk.CTkEntry(master=self.frame)
        self.lessons_entry.pack(pady=5)
        
        self.verbose_var = ctk.BooleanVar()
        ctk.CTkCheckBox(master=self.frame, text="Enable Verbose", font=("", 14), variable=self.verbose_var).pack(pady=5)
        
        ctk.CTkButton(master=self.frame, text="Save", command=self.save_config).pack(pady=5)
        
        self.update_settings()
        self.grab_set()
        self.lift()
        self.focus_force()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def save_config(self):
        duolingo_jwt = self.jwt_entry.get()
        lessons = self.lessons_entry.get()
        verbose = self.verbose_var.get()
        config['Settings'] = {
            'DUOLINGO_JWT': duolingo_jwt,
            'LESSONS': lessons,
            'VERBOSE': str(verbose),
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        result = CTkMessagebox(title="Settings", message="Settings saved successfully!", icon="check", option_1="OK").get()
        if result == "OK":
            self.close_window()
        self.main_window.settings_updated()

    def update_settings(self):
        settings = read_config()
        if settings:
            self.jwt_entry.delete(0, ctk.END)
            self.jwt_entry.insert(0, settings['DUOLINGO_JWT'])
            self.lessons_entry.delete(0, ctk.END)
            self.lessons_entry.insert(0, settings['LESSONS'])
            self.verbose_var.set(settings.getboolean('VERBOSE', False))
            
    def on_close(self):
        self.main_window.settings_window_closed()
        self.destroy()

    def close_window(self):
        self.on_close()

class InfoWindow(ctk.CTkToplevel):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.title('About')
        self.geometry("350x300")
        self.resizable(False, False)
        
        self.frame = ctk.CTkFrame(master=self)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)

        ctk.CTkLabel(master=self.frame, text="About DuoXPy GUI Edition", font=("", 16, "bold")).pack(pady=5)
        ctk.CTkLabel(master=self.frame, text="Main developer: GorouFlex", font=("", 15)).pack(pady=2)
        ctk.CTkLabel(master=self.frame, text=f"Version: {VERSION} (2NSNH2024)", font=("", 14)).pack(pady=2)
        ctk.CTkButton(master=self.frame, text="Open Github", font=("", 12), command=self.open_github).pack(pady=5)
        ctk.CTkButton(master=self.frame, text="Change log", font=("", 12), command=self.open_releases).pack(pady=5)
        ctk.CTkButton(master=self.frame, text="Switch to CLI Edition", font=("", 12), command=self.switch_to_cli).pack(pady=5)

        latest_version = get_latest_ver()
        ctk.CTkLabel(master=self.frame, width=200, text=f"Latest stable version on Github: {latest_version}", font=("", 14)).pack(pady=5)
        
        self.grab_set()
        self.lift()
        self.focus_force()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def open_github(self):
        webbrowser.open(f"https://github.com/{GITHUB_REPO}")

    def open_releases(self):
        webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases")

    def switch_to_cli(self):
        result = CTkMessagebox(title="Switch to CLI Edition", message="Are you sure you want to switch to the CLI edition?", icon="question", option_1="Yes", option_2="No").get()
        if result == "Yes":
            try:
                cli_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{CLI_FILE_PATH}"
                response = urllib.request.urlopen(cli_url)
                data = response.read().decode('utf-8')
                with open(__file__, 'w', encoding='utf-8') as f:
                    f.write(data)
                CTkMessagebox(title="Switch to CLI", message="Switched to CLI edition successfully. Restarting the application...", icon="check", option_1="OK")
                raise SystemExit
            except Exception as e:
                CTkMessagebox(title="Error", message=f"Failed to switch to CLI edition: {e}", icon="cancel", option_1="OK")

    def on_close(self):
        self.main_window.info_window_closed()
        self.destroy()

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DuoXPy")
        self.geometry("300x250")
        self.resizable(False, False)
        self.frame = ctk.CTkFrame(master=self)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(master=self.frame, text="DuoXPy", font=("", 16, "bold")).pack(pady=10)
        ctk.CTkButton(master=self.frame, text="Start", font=("", 12), command=self.run_duoxpy).pack(pady=5)
        ctk.CTkButton(master=self.frame, text="Settings", font=("", 12), command=self.open_settings).pack(pady=5)
        ctk.CTkButton(master=self.frame, text="About", font=("", 12), command=self.open_about).pack(pady=5)
        ctk.CTkLabel(master=self.frame, text=f"Version: {VERSION}", font=("", 12)).pack(pady=10)
        
        self.info_window = None
        self.settings_window = None
        self.task_thread = None
        self.progress_popup = None  
        self.stop_event = threading.Event()
        check_updates()
        self.check_config_and_open_settings()

    def open_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow(self)

    def open_about(self):
        if not self.info_window:
            self.info_window = InfoWindow(self)

    def info_window_closed(self):
        self.info_window = None

    def settings_window_closed(self):
        self.settings_window = None

    def check_config_and_open_settings(self):
        if not read_config():
            self.open_settings()

    def settings_updated(self):
        pass

    def run_duoxpy(self):
        if self.progress_popup is not None and self.progress_popup.winfo_exists():
            result = CTkMessagebox(title="Runner Already Active", message="A runner is already active. Please close it before starting a new one.", icon="warning", option_1="Close Previous", option_2="Cancel").get()
            if result == "Close Previous":
                self.close_progress_popup()
            else:
                return
        
        settings = read_config()
        if not settings:
            CTkMessagebox(title="Error", message="Settings is missing or incomplete.", icon="cancel", option_1="OK")
            return
        
        duolingo_jwt = settings['DUOLINGO_JWT']
        lessons = int(settings['LESSONS'])
        verbose = settings.getboolean('VERBOSE', False)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {duolingo_jwt}",
            "User-Agent": "Mozilla/5.0"
        }

        self.progress_popup = ctk.CTkToplevel(self)
        self.progress_popup.title("Runner")
        if verbose:
           self.progress_popup.geometry("325x300")
        else:
           self.progress_popup.geometry("325x125")
           self.progress_popup.resizable(False, False)

        self.progress_popup.grab_set()
        self.progress_popup.lift()
        self.progress_popup.focus_force()

        self.progress_popup.protocol("WM_DELETE_WINDOW", self.on_close_progress_popup)
        
        self.progress_label = ctk.CTkLabel(master=self.progress_popup, text="Make sure you have a strong and stable Internet\nDo not sleep while running DuoXPy")
        self.progress_label.pack(pady=10)
        self.popup_progress_bar = ctk.CTkProgressBar(master=self.progress_popup)
        self.popup_progress_bar.pack(pady=5)
        self.cancel_button = ctk.CTkButton(master=self.progress_popup, text="Cancel", font=("", 12), command=self.confirm_cancel)
        self.cancel_button.pack(pady=5)
        self.result_text = ctk.CTkTextbox(master=self.progress_popup)
        if verbose:
            self.result_text.pack(pady=5, padx=10, fill="both", expand=True)
        
        self.task_index = 0
        self.xp = 0
        self.lessons = lessons
        self.verbose = verbose
        self.headers = headers
        self.duolingo_jwt = duolingo_jwt
        self.fromLanguage = None
        self.learningLanguage = None

        self.stop_event.clear()
        self.task_thread = threading.Thread(target=self.run_task)
        self.task_thread.start()

    def on_close_progress_popup(self):
        self.confirm_cancel()

    def confirm_cancel(self):
        if self.task_thread.is_alive():
            result = CTkMessagebox(title="Cancel Runner", message="Are you sure you want to cancel the runner?", icon="warning", option_1="Yes", option_2="No").get()
            if result == "Yes":
                self.stop_event.set()
                self.progress_popup.destroy()
                self.progress_popup = None
        else:
            self.progress_popup.destroy()
            self.progress_popup = None

    def run_task(self):
        try:
            sub = decode_jwt(self.duolingo_jwt)['sub']
            user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
            status, user_info_data = http_request("GET", user_info_url, self.headers)
            user_info = json.loads(user_info_data)
            self.fromLanguage = user_info['fromLanguage']
            self.learningLanguage = user_info['learningLanguage']

            for i in range(self.lessons):
                if self.stop_event.is_set():
                    break
                try:
                    session_payload = json.dumps({
                        "challengeTypes": ["assist", "characterIntro", "characterMatch", "characterPuzzle", "characterSelect", "characterTrace", "characterWrite",
                                           "completeReverseTranslation", "definition", "dialogue", "extendedMatch", "extendedListenMatch", "form", "freeResponse",
                                           "gapFill", "judge", "listen", "listenComplete", "listenMatch", "match", "name", "listenComprehension", "listenIsolation",
                                           "listenSpeak", "listenTap", "orderTapComplete", "partialListen", "partialReverseTranslate", "patternTapComplete", "radioBinary",
                                           "radioImageSelect", "radioListenMatch", "radioListenRecognize", "radioSelect", "readComprehension", "reverseAssist",
                                           "sameDifferent", "select", "selectPronunciation", "selectTranscription", "svgPuzzle", "syllableTap", "syllableListenTap",
                                           "speak", "tapCloze", "tapClozeTable", "tapComplete", "tapCompleteTable", "tapDescribe", "translate", "transliterate",
                                           "transliterationAssist", "typeCloze", "typeClozeTable", "typeComplete", "typeCompleteTable", "writeComprehension"],
                        "fromLanguage": self.fromLanguage,
                        "isFinalLevel": False,
                        "isV2": True,
                        "juicy": True,
                        "learningLanguage": self.learningLanguage,
                        "smartTipsVersion": 2,
                        "type": "GLOBAL_PRACTICE"
                    })
                    session_url = "https://www.duolingo.com/2017-06-30/sessions"
                    status, session_data = http_request("POST", session_url, self.headers, session_payload.encode())
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
                    status, response_data = http_request("PUT", update_url, self.headers, update_payload.encode())
                    response = json.loads(response_data)
                    self.xp += response['xpGain']
                    self.update_progress(i + 1)
                    if self.verbose:
                        self.update_result_text(f"[{i+1}] - {response['xpGain']} XP\n")
                except Exception as e:
                    if self.verbose:
                        self.update_result_text(f"An error occurred during lesson {i+1}: {e}\n")
        except Exception as error:
            if self.verbose:
                self.update_result_text(f"❌ Something went wrong: {error}\n")
        finally:
            CTkMessagebox(title="Runner", message=f"Done. You won {self.xp} XP", icon="check", option_1="OK")
            self.after(0, self.runner_done)

    def update_progress(self, value):
        self.after(0, lambda: self.safe_update(self.popup_progress_bar, value / self.lessons))

    def update_result_text(self, text):
        self.after(0, lambda: self.safe_insert(self.result_text, ctk.END, text))

    def safe_update(self, widget, value):
        if widget.winfo_exists():
            widget.set(value)

    def safe_insert(self, widget, index, text):
        if widget.winfo_exists():
            widget.insert(index, text)

    def runner_done(self):
        if self.progress_popup is not None:
            self.progress_popup.protocol("WM_DELETE_WINDOW", self.close_progress_popup)
            self.cancel_button.configure(text="Exit", command=self.close_progress_popup)
            self.progress_popup.lift()
            self.progress_popup.focus_force()

    def close_progress_popup(self):
        if self.progress_popup is not None:
            self.progress_popup.destroy()
            self.progress_popup = None

def read_config():
    if os.path.isfile(CONFIG_FILE) and os.stat(CONFIG_FILE).st_size > 0:
        config.read(CONFIG_FILE)
        return config['Settings']
    return None

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
                time.sleep(5)
            else:
                if CTkMessagebox(title="Update Check", message="Failed to fetch latest version. \nDo you want to skip the check for updates?", icon="warning", option_1="Yes", option_2="No").get() == "Yes":
                    skip_update_check = True
                else:
                    raise SystemExit
    if not skip_update_check:
        if LOCAL_VERSION < latest_version:
            if CTkMessagebox(title="Update Available", message=f"New version available: {latest_version}. \nDo you want to update the script?", icon="question", option_1="Yes", option_2="No").get() == "Yes":
                updater()
                raise SystemExit
        elif LOCAL_VERSION > latest_version:
            if CTkMessagebox(title="DuoXPy Beta Program", message="Welcome to the DuoXPy Beta Program. This beta build may not work as expected and is only for testing purposes! Do you want to continue?", icon="question", option_1="Yes", option_2="No").get() == "No":
                raise SystemExit

def updater():
    latest_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/GUI/DuoXPy-GUI.py"
    response = urllib.request.urlopen(latest_url)
    data = response.read().decode('utf-8')
    with open(__file__, 'w', encoding='utf-8') as f:
        f.write(data)
    CTkMessagebox(title="Update", message="Script updated successfully. Restarting the application...", icon="check", option_1="OK")
    raise SystemExit

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("green")
    app = MainWindow()
    app.mainloop()
