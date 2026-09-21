import mss
from PIL import Image


class ScreenObserver:

    def __init__(self):

        self.sct = mss.mss()

        # Primary monitor.
        self.monitor = self.sct.monitors[1]

    def capture(self):

        screenshot = self.sct.grab(
            self.monitor
        )

        return Image.frombytes(
            "RGB",
            screenshot.size,
            screenshot.rgb
        )

    def observe(self):

        return {
            "image": self.capture()
        }

    def close(self):

        self.sct.close()