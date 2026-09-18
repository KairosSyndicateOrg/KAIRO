import mss
from PIL import Image


class ScreenObserver:
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]

    def capture(self):
        screenshot = self.sct.grab(self.monitor)

        return Image.frombytes(
            "RGB",
            screenshot.size,
            screenshot.rgb
        )

    def observe(self):
        image = self.capture()

        return {
            "image": image
        }