from PySide6.QtCore import QObject, Slot, Signal

from agent import Agent


class KairoBridge(QObject):

    status_changed = Signal(str)

    def __init__(self):
        super().__init__()

        self.agent = Agent()

    @Slot(str)
    def run_task(self, command):

        self.status_changed.emit("PLANNING")

        try:
            self.agent.run(command)

            self.status_changed.emit("COMPLETED")

        except Exception as e:

            print(f"[KAIRO ERROR] {e}")

            self.status_changed.emit("ERROR")