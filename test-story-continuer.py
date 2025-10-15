import pyautogui
import pydirectinput
import time

pyautogui.FAILSAFE = False

image_path = "test-story-continuer.png"

i = 0
while True:
    i += 1
    try:
        location = pyautogui.locateCenterOnScreen(image_path)
        if location:
            print(f"Found at {location}, clicking...")
            pydirectinput.click(location.x, location.y)
            pyautogui.move(location.x, location.y - 200)
    except pyautogui.ImageNotFoundException:
        print("." * (i % 10), end="\r")
    time.sleep(0.25)
