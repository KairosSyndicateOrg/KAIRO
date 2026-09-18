import pyautogui
import time


def move(x, y, duration=0.45):
    pyautogui.moveTo(
        x,
        y,
        duration=duration,
        tween=pyautogui.easeInOutQuad
    )


def click(x, y):
    pyautogui.click(x, y)


def type_text(text):
    pyautogui.write(text, interval=0.02)


def press(key):
    pyautogui.press(key)


def hotkey(*keys):
    pyautogui.hotkey(*keys)


def wait(seconds=0.5):
    time.sleep(seconds)