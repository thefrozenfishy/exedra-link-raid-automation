import pytesseract
import pyautogui
import pydirectinput
import pygetwindow
import cv2
import os
import numpy as np
from PIL import ImageGrab, Image
from enum import Enum

debug = True
if debug:
    os.makedirs("debug", exist_ok=True)

lvl_inp = input(
    'Please enter levels to run as a single level or with a hyphen between. Examples: "9-12" or "8": Default 9-12: '
)
if "-" in lvl_inp:
    start, end = map(int, lvl_inp.split("-"))
    LEVELS_TO_FIND = list(range(start, end + 1))
elif not lvl_inp.isdigit():
    LEVELS_TO_FIND = [9, 10, 11, 12]
else:
    LEVELS_TO_FIND = [int(lvl_inp)]

host_inp = input('Host or Join? "H" or "J". Default Join: ').lower()
host = host_inp and host_inp[0] == "h"

# Config
TARGET_WINDOW = "MadokaExedra"
MAX_SCROLL_ATTEMPTS = 20


def get_game_window():
    wins = pygetwindow.getWindowsWithTitle(TARGET_WINDOW)
    if not wins:
        raise RuntimeError("Game window not found")
    return wins[0]


def confirm_desired_difficulty(data, levels):
    for i, text in enumerate(data["text"]):
        if not text.strip():
            continue
        if (
            "lvl" in text.lower()
            and data["text"][i + 1].strip().isdigit()
            and int(data["text"][i + 1]) in levels
        ):
            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i] + data["width"][i + 1],
                data["height"][i],
            )
            return x, y, w, h


def start_join():
    for attempt in range(MAX_SCROLL_ATTEMPTS):
        data = get_img("battle_box")
        match = confirm_desired_difficulty(data, LEVELS_TO_FIND)

        if match:
            x, y, w, h = match
            pyautogui.click(
                text_locations["battle_box"][0] + x + w // 2,
                text_locations["battle_box"][1] + y + h // 2,
            )
            pyautogui.sleep(0.5)
            pydirectinput.click(
                text_locations["join_button"][0], text_locations["join_button"][1]
            )
            pyautogui.sleep(1)
            pydirectinput.click(
                text_locations["play_button"][0], text_locations["play_button"][1]
            )

            pyautogui.sleep(2)
            return

        pyautogui.moveTo(
            text_locations["center_of_screen"][0],
            text_locations["center_of_screen"][1],
        )
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)

    # Refreshing
    pydirectinput.click(
        text_locations["refresh_button"][0], text_locations["refresh_button"][1]
    )


class CurrentState(Enum):
    JOIN_SCREEN = "JOIN_SCREEN"
    HOST_SCREEN = "HOST_SCREEN"
    HOME_SCREEN = "HOME_SCREEN"
    BATTLE_SCREEN = "BATTLE_SCREEN"
    RESULTS_SCREEN = "RESULTS_SCREEN"
    BACK_SCREEN = "BACK_SCREEN"


def get_img(cords: str):
    img = ImageGrab.grab(text_locations[cords])
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    gray = cv2.bitwise_not(gray)

    if debug:
        img.save(f"debug/{cords}.png")
        Image.fromarray(gray).save(f"debug/{cords}_gray.png")
    return pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)


def current_state() -> CurrentState:
    data = get_img("result_box")
    for text in data["text"]:
        if "Lvl" in text:
            return CurrentState.RESULTS_SCREEN

    data = get_img("battle_box")
    for text in data["text"]:
        if "lvl" in text.lower():
            return CurrentState.JOIN_SCREEN

    data = get_img("host_box")
    for text in data["text"]:
        if "ready" in text.lower():
            return CurrentState.HOST_SCREEN

    data = get_img("like_box")
    for text in data["text"]:
        if text.isdigit():
            return CurrentState.HOME_SCREEN

    data = get_img("back_box")
    for text in data["text"]:
        if "Back" in text:
            return CurrentState.BACK_SCREEN

    return CurrentState.BATTLE_SCREEN


text_locations = {}


def setup_text_locations():
    win = get_game_window()
    try:
        win.activate()
    except Exception as e:
        print(
            f'Could not activate window: {e}.\nThis is not a major issue, just be sure that no application is hiding Exedra from view, \n\
The OCR has to "see" the content of the game to determine what to do.'
        )
    text_locations["result_box"] = (
        win.left + 0.23 * win.width,
        win.top + 0.795 * win.height,
        win.right - 0.725 * win.width,
        win.bottom - 0.172 * win.height,
    )
    text_locations["back_box"] = (
        win.left + 0.45 * win.width,
        win.top + 0.82 * win.height,
        win.right - 0.45 * win.width,
        win.bottom - 0.12 * win.height,
    )
    text_locations["join_button"] = (
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["play_button"] = (
        int(win.right - 0.5 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["refresh_button"] = (
        int(win.left + 0.31 * win.width),
        int(win.top + 0.09 * win.height),
    )
    text_locations["join_screen_button"] = (
        int(win.left + 0.7 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["host_screen_button"] = (
        int(win.left + 0.3 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["center_of_screen"] = (
        win.left + win.width // 2,
        win.top + win.height // 2,
    )
    text_locations["like_box"] = (
        win.left + 0.12 * win.width,
        win.top + 0.15 * win.height,
        win.right - 0.83 * win.width,
        win.bottom - 0.75 * win.height,
    )
    text_locations["battle_box"] = (
        win.left + 0.475 * win.width,
        win.top + 0.1 * win.height,
        win.right - 0.465 * win.width,
        win.bottom - 0.6 * win.height,
    )
    text_locations["host_box"] = (
        win.left + 0.7 * win.width,
        win.top + 0.76 * win.height,
        win.right - 0.15 * win.width,
        win.bottom - 0.18 * win.height,
    )


def main():
    while True:
        pyautogui.sleep(1)
        state = current_state()
        print("Current State:", state.name)
        match state:
            case CurrentState.JOIN_SCREEN:
                start_join()
            case CurrentState.HOST_SCREEN:
                pydirectinput.click(
                    int(text_locations["host_box"][0]),
                    int(text_locations["host_box"][1]),
                )
            case CurrentState.HOME_SCREEN:
                key = "host_screen_button" if host else "join_screen_button"
                pydirectinput.click(text_locations[key][0], text_locations[key][1])
            case CurrentState.BATTLE_SCREEN:
                pyautogui.sleep(5)
                # No need to ping the process that much while in battle.
            case CurrentState.RESULTS_SCREEN:
                pydirectinput.click(
                    int(text_locations["result_box"][0]),
                    int(text_locations["result_box"][1]),
                )
            case CurrentState.BACK_SCREEN:
                pydirectinput.click(
                    int(text_locations["back_box"][0]),
                    int(text_locations["back_box"][1]),
                )


if __name__ == "__main__":
    setup_text_locations()
    main()
