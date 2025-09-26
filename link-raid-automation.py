import pytesseract
import pyautogui
import pydirectinput
import pygetwindow
import keyboard
import cv2
import os
import re
import numpy as np
from PIL import ImageGrab, Image
from enum import Enum
import configparser
from datetime import datetime
import logging
from pathlib import Path
from requests import get

CONFIG_FILE = "link-raid-automation-settings.ini"

config = configparser.ConfigParser()
defaults = {
    "host_team": "LR Auto 8",
    "join_team": "LR Auto 9-12",
    "join_diff": "9-12",
    "debug_mode": "false",
    "document_daily_reward": "true",
    "exe_name": "MadokaExedra",
    "max_scroll_attempts": "40",
    "friends_only": "false",
    "community_only": "false",
}

config.read(CONFIG_FILE)
config["general"] = {
    **defaults,
    **(config["general"] if "general" in config else {}),
}

with open(CONFIG_FILE, "w", encoding="utf-8", newline="\n") as f:
    config.write(f)

DEBUG = config.getboolean("general", "debug_mode")
if DEBUG:
    os.makedirs("debug/logs", exist_ok=True)

HOST_TEAM = config.get("general", "host_team").replace(" ", "").lower()
JOIN_TEAM = config.get("general", "join_team").replace(" ", "").lower()
JOIN_DIFF = config.get("general", "join_diff")
if "-" in JOIN_DIFF:
    start, end = map(int, JOIN_DIFF.split("-"))
    LEVELS_TO_FIND = list(map(str, range(start, end + 1)))
else:
    LEVELS_TO_FIND = [JOIN_DIFF]

DAILY_SCREENSHOT = config.getboolean("general", "document_daily_reward")
TARGET_WINDOW = config.get("general", "exe_name")
MAX_SCROLL_ATTEMPTS = config.getint("general", "max_scroll_attempts")

FRIENDS_ONLY = config.getboolean("general", "friends_only")
COMMUNITY_ONLY = config.getboolean("general", "community_only")

keyboard.add_hotkey("ctrl+shift+q", lambda: os._exit(0))

log_formatter = logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("lr_automation")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

if DEBUG:
    file_handler = logging.FileHandler(
        f"debug/logs/{datetime.today().strftime('%Y-%m-%dT%H-%M-%S')}.txt",
        encoding="utf-8",
    )
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)


FRIEND_FILE = "friends.txt"
friend_file = Path(FRIEND_FILE)
friend_file.touch(exist_ok=True)
friends = [
    re.sub(r"[^A-Za-z0-9]", "", f.lower().replace(" ", ""))
    for f in friend_file.read_text(encoding="utf-8").split("\n")
]
friends = {f for f in friends if len(f) > 2}
resp = get(
    "https://raw.githubusercontent.com/thefrozenfishy/exedra-link-raid-automation/main/community.txt",
    timeout=10,
)
if resp.ok:
    community = [
        re.sub(r"[^A-Za-z0-9]", "", f.lower().replace(" ", ""))
        for f in resp.text.splitlines()
    ]
else:
    logging.error("Failed to fetch community members list.")
    community = []
community = {c for c in community if len(c) > 2}


def get_game_window():
    wins = pygetwindow.getWindowsWithTitle(TARGET_WINDOW)
    if not wins:
        raise RuntimeError("Game window not found")
    return wins[0]


def get_data_in_img(cords: str):
    img = ImageGrab.grab(text_locations[cords])
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    gray = cv2.bitwise_not(gray)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    if DEBUG:
        img.save(f"debug/{cords}.png")
        Image.fromarray(gray).save(f"debug/{cords}_gray.png")
        logger.info("%s > %s", cords, data["text"])
    return data


def get_text_in_img(cords: str) -> str:
    data = get_data_in_img(cords)
    return re.sub(r"[^A-Za-z0-9]", "", "".join(data["text"]).lower().replace(" ", ""))


def find_coords_for_difficulties():
    data = get_data_in_img("battle_box")
    for i, text in enumerate(data["text"]):
        text: str
        if "lvl" in text.lower().replace("i", "l") and (
            COMMUNITY_ONLY
            or FRIENDS_ONLY
            or any(text.endswith(s) for s in LEVELS_TO_FIND)
            or (
                len(data["text"]) > i + 1
                and any(s in data["text"][i + 1] for s in LEVELS_TO_FIND)
            )
        ):
            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i]
                + (data["width"][i + 1] if len(data["width"]) > i + 1 else 0),
                data["height"][i],
            )
            return x, y, w, h
    return 0, 0, 0, 0


def start_join():
    for attempt in range(MAX_SCROLL_ATTEMPTS):
        logger.debug("Scroll attempt %2d/%d", attempt + 1, MAX_SCROLL_ATTEMPTS)
        x, y, w, h = find_coords_for_difficulties()
        if x and y and w and h:
            run = True
            if FRIENDS_ONLY or COMMUNITY_ONLY:

                img = ImageGrab.grab(
                    (
                        text_locations["battle_box"][0]
                        + x
                        - text_locations["resolution"][0] // 4.16,
                        text_locations["battle_box"][1]
                        + y
                        + text_locations["resolution"][1] // 10.25,
                        text_locations["battle_box"][0]
                        + x
                        - text_locations["resolution"][0] // 18,
                        text_locations["battle_box"][1]
                        + y
                        + text_locations["resolution"][1] // 7.4,
                    )
                )
                if DEBUG:
                    img.save("debug/join_player_name.png")
                gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
                gray = cv2.bitwise_not(gray)
                data = pytesseract.image_to_data(
                    gray, output_type=pytesseract.Output.DICT
                )
                player_name = "".join(data["text"]).replace(" ", "")
                logger.debug("Found player name: %s", player_name)
                if not (
                    (FRIENDS_ONLY and player_name in friends)
                    or (COMMUNITY_ONLY and player_name in community)
                ):
                    run = False

            if run:
                click(
                    text_locations["battle_box"][0] + x + w // 2,
                    text_locations["battle_box"][1] + y + h // 2,
                )
                pyautogui.sleep(0.5)

                click(
                    text_locations["join_button"][0], text_locations["join_button"][1]
                )
                return

        pydirectinput.moveTo(
            text_locations["scroll_location"][0],
            text_locations["scroll_location"][1],
        )
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)

    # Refreshing
    click(text_locations["refresh_button"][0], text_locations["refresh_button"][1])


class CurrentState(Enum):
    JOIN_SCREEN = "JOIN_SCREEN"
    HOST_SCREEN = "HOST_SCREEN"
    HOME_SCREEN_CAN_HOST = "HOME_SCREEN_CAN_HOST"
    HOME_SCREEN_CANNOT_HOST = "HOME_SCREEN_CANNOT_HOST"
    NO_ACTION = "NO_ACTION"
    RESULTS_SCREEN = "RESULTS_SCREEN"
    BACK_SCREEN = "BACK_SCREEN"
    PLAY_JOIN_SCREEN = "PLAY_JOIN_SCREEN"
    PLAY_HOST_SCREEN = "PLAY_HOST_SCREEN"
    DAILY_BONUS_COUNTER = "DAILY_BONUS_COUNTER"
    DAILY_BONUS = "DAILY_BONUS"
    CONTINUE = "CONTINUE"


def current_state() -> CurrentState:
    text = get_text_in_img("result_box")
    if "lvl" in text.lower().replace("i", "l"):
        return CurrentState.RESULTS_SCREEN

    text = get_text_in_img("join_button_box")
    if "joln" in text.lower().replace("i", "l"):
        return CurrentState.JOIN_SCREEN

    text = get_text_in_img("daily_bonus_box")
    if "dally" in text.lower().replace("i", "l"):
        return CurrentState.DAILY_BONUS_COUNTER

    text = get_text_in_img("host_diff_box")
    if "lvl" in text.lower().replace("i", "l"):
        return CurrentState.HOST_SCREEN

    text = get_text_in_img("back_box")
    if "back" in text.lower():
        return CurrentState.BACK_SCREEN

    text = get_text_in_img("party_box")
    if "party" in text.lower():
        text2 = get_text_in_img("play_box")
        if "play" in text2.lower():
            return CurrentState.PLAY_JOIN_SCREEN
        return CurrentState.PLAY_HOST_SCREEN

    text = get_text_in_img("like_box")
    if text.isdigit():
        text4 = get_text_in_img("in_progress_box")
        if "vlewresults" in text4.lower().replace("i", "l"):
            return CurrentState.HOME_SCREEN_CAN_HOST

        text2 = get_text_in_img("can_host_box")
        text3 = get_text_in_img("in_progress_box")
        if (
            "progress" not in text3.lower()
            and "play" in text2.lower()
            and "06" not in text2
        ):
            return CurrentState.HOME_SCREEN_CAN_HOST
        return CurrentState.HOME_SCREEN_CANNOT_HOST

    text = get_text_in_img("daily_reward_box")
    if "ob" in text.lower().replace("i", "l"):
        return CurrentState.DAILY_BONUS

    text = get_text_in_img("tap_to_continue")
    if "contlnue" in text.lower().replace("i", "l"):
        return CurrentState.CONTINUE

    return CurrentState.NO_ACTION


text_locations = {}


def click(x: float | int, y: float | int):
    pydirectinput.click(int(x), int(y))
    pyautogui.moveTo(10, 10)


def setup_text_locations():
    win = get_game_window()
    try:
        win.activate()
    except Exception as e:
        logger.exception(
            """Could not activate window!
This is not a major issue, just be sure that no application is hiding Exedra from view. 
The OCR has to 'see' the content of the game to determine what to do.""",
            exc_info=e,
        )
    text_locations["result_box"] = (
        win.left + 0.23 * win.width,
        win.top + 0.785 * win.height,
        win.right - 0.725 * win.width,
        win.bottom - 0.172 * win.height,
    )
    text_locations["daily_bonus_box"] = (
        win.left + 0.3 * win.width,
        win.top + 0.1 * win.height,
        win.right - 0.3 * win.width,
        win.bottom - 0.7 * win.height,
    )
    text_locations["daily_reward_box"] = (
        win.left + 0.4 * win.width,
        win.top + 0.28 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.62 * win.height,
    )
    text_locations["daily_reward_pic_box"] = (
        win.left + 0.35 * win.width,
        win.top + 0.35 * win.height,
        win.right - 0.35 * win.width,
        win.bottom - 0.4 * win.height,
    )
    text_locations["back_box"] = (
        win.left + 0.45 * win.width,
        win.top + 0.81 * win.height,
        win.right - 0.45 * win.width,
        win.bottom - 0.12 * win.height,
    )
    text_locations["team_name"] = (
        win.left + 0.4 * win.width,
        win.top + 0.44 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.5 * win.height,
    )
    text_locations["party_box"] = (
        win.left + 0.29 * win.width,
        win.top + 0.44 * win.height,
        win.right - 0.65 * win.width,
        win.bottom - 0.5 * win.height,
    )
    text_locations["play_box"] = (
        win.left + 0.5 * win.width,
        win.top + 0.79 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.15 * win.height,
    )
    text_locations["join_button"] = (
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["join_button_box"] = (
        win.left + 0.8 * win.width,
        win.top + 0.8 * win.height,
        win.right - 0.12 * win.width,
        win.bottom - 0.14 * win.height,
    )
    text_locations["play_button"] = (
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["refresh_button"] = (
        int(win.left + 0.31 * win.width),
        int(win.top + 0.09 * win.height),
    )
    text_locations["join_screen_button"] = (
        int(win.left + 0.7 * win.width),
        int(win.top + 0.82 * win.height),
    )
    text_locations["host_screen_button"] = (
        int(win.left + 0.3 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["next_team"] = (
        int(win.left + 0.28 * win.width),
        int(win.top + 0.58 * win.height),
    )
    text_locations["scroll_location"] = (
        win.left + 2 * win.width // 3,
        win.top + win.height // 2,
    )
    text_locations["like_box"] = (
        win.left + 0.12 * win.width,
        win.top + 0.14 * win.height,
        win.right - 0.83 * win.width,
        win.bottom - 0.75 * win.height,
    )
    text_locations["battle_box"] = (
        win.left + 0.475 * win.width,
        win.top + 0.18 * win.height,
        win.right - 0.465 * win.width,
        win.bottom - 0.5 * win.height,
    )
    text_locations["host_diff_box"] = (
        win.left + 0.68 * win.width,
        win.top + 0.17 * win.height,
        win.right - 0.22 * win.width,
        win.bottom - 0.79 * win.height,
    )
    text_locations["host_box"] = (
        int(win.left + 0.73 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["can_host_box"] = (
        win.left + 0.32 * win.width,
        win.top + 0.82 * win.height,
        win.right - 0.57 * win.width,
        win.bottom - 0.13 * win.height,
    )
    text_locations["in_progress_box"] = (
        win.left + 0.3 * win.width,
        win.top + 0.75 * win.height,
        win.right - 0.55 * win.width,
        win.bottom - 0.15 * win.height,
    )
    text_locations["tap_to_continue"] = (
        win.left + 0.4 * win.width,
        win.top + 0.85 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.05 * win.height,
    )
    text_locations["resolution"] = (win.width, win.height)


def select_correct_team(team_name):
    for _ in range(10):
        if team_name.lower() in get_text_in_img("team_name"):
            return
        click(text_locations["next_team"][0], text_locations["next_team"][1])
        pyautogui.sleep(0.2)
    raise RuntimeError(f'Could not find team named "{team_name}"')


def main():
    setup_text_locations()
    logger.info("starting with config: %s", dict(config["general"]))
    logger.info(
        "Considering %d friends and %s community members", len(friends), len(community)
    )
    logger.info("Press Ctrl+Shift+Q to terminate the program.")
    while True:
        pyautogui.sleep(1)
        state = current_state()
        logger.info("Current State: %s", state.name)
        match state:
            case CurrentState.JOIN_SCREEN:
                start_join()
            case CurrentState.HOST_SCREEN:
                click(
                    text_locations["host_box"][0],
                    text_locations["host_box"][1],
                )
            case CurrentState.HOME_SCREEN_CAN_HOST:
                click(
                    text_locations["host_screen_button"][0],
                    text_locations["host_screen_button"][1],
                )
            case CurrentState.HOME_SCREEN_CANNOT_HOST:
                click(
                    text_locations["join_screen_button"][0],
                    text_locations["join_screen_button"][1],
                )
            case CurrentState.PLAY_JOIN_SCREEN:
                select_correct_team(JOIN_TEAM)
                logger.info("Joining a game...")
                click(
                    text_locations["play_button"][0], text_locations["play_button"][1]
                )
                pyautogui.sleep(2)
            case CurrentState.PLAY_HOST_SCREEN:
                select_correct_team(HOST_TEAM)
                logger.info("Hosting a game...")
                click(
                    text_locations["play_button"][0], text_locations["play_button"][1]
                )
                pyautogui.sleep(2)
            case CurrentState.NO_ACTION:
                pyautogui.sleep(5)
            case CurrentState.RESULTS_SCREEN:
                click(
                    int(text_locations["result_box"][2]),
                    int(text_locations["result_box"][3]),
                )
            case CurrentState.BACK_SCREEN:
                click(
                    int(text_locations["back_box"][0]),
                    int(text_locations["back_box"][1]),
                )
                pyautogui.sleep(2)
            case CurrentState.CONTINUE:
                click(
                    int(text_locations["back_box"][0]),
                    int(text_locations["back_box"][1]),
                )
            case CurrentState.DAILY_BONUS_COUNTER:
                click(
                    int(text_locations["back_box"][0]),
                    int(text_locations["back_box"][1]),
                )
            case CurrentState.DAILY_BONUS:
                if DAILY_SCREENSHOT:
                    img = ImageGrab.grab(text_locations["daily_reward_pic_box"])
                    os.makedirs("daily_reward", exist_ok=True)
                    img.save(
                        f"daily_reward/{datetime.today().strftime('%Y-%m-%dT%H-%M-%S')}.png"
                    )

                click(
                    int(text_locations["back_box"][0]),
                    int(text_locations["back_box"][1]),
                )


if __name__ == "__main__":
    main()
