import os
import json
import base64
import requests
from datetime import datetime

LESSONS = int(os.getenv('LESSONS', 1))
DUOLINGO_JWT = os.getenv('DUOLINGO_JWT')
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {DUOLINGO_JWT}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def decode_jwt(jwt):
    _, payload, _ = jwt.split('.')
    decoded = base64.urlsafe_b64decode(payload + "==")
    return json.loads(decoded)

print("--- Welcome to DuoXPy Core Edition ---")
print("Made by GorouFlex - Version 1.0")
print(f"Lessons: {LESSONS}")
print("Running...")
print()
try:
    sub = decode_jwt(DUOLINGO_JWT)['sub']
    user_info_url = f"https://www.duolingo.com/2017-06-30/users/{sub}?fields=fromLanguage,learningLanguage"
    user_info = requests.get(user_info_url, headers=headers).json()
    fromLanguage = user_info['fromLanguage']
    learningLanguage = user_info['learningLanguage']
    xp = 0
    for _ in range(LESSONS):
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
    print(f"🎉 You won {xp} XP")
except Exception as error:
    print("❌ Something went wrong")
    print(str(error))
