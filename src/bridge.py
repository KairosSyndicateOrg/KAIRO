from PySide6.QtCore import QObject, Signal, Slot, QThread

from agent import Agent


class AgentWorker(QObject):

    status_changed = Signal(str)
    finished = Signal(bool)
    error = Signal(str)

    def __init__(
        self,
        command,
        cursor_model=None
    ):

        super().__init__()

        self.command = command
        self.cursor_model = cursor_model

    @Slot()
    def run(self):

        try:

            self.status_changed.emit(
                "PLANNING"
            )

            agent = Agent(
                cursor_model=self.cursor_model
            )

            self.status_changed.emit(
                "EXECUTING"
            )

            success = agent.run(
                self.command
            )

            self.finished.emit(
                bool(success)
            )

        except Exception as e:

            print(
                f"[KAIRO ERROR] {e}"
            )

            self.error.emit(
                str(e)
            )


class KairoBridge(QObject):

    status_changed = Signal(str)

    def __init__(self):

        super().__init__()

        self.thread = None
        self.worker = None

    @Slot(str)
    def run_task(
        self,
        command
    ):

        # Prevent starting two tasks at once.
        if self.thread is not None:

            if self.thread.isRunning():

                return

        self.thread = QThread()

        self.worker = AgentWorker(
            command
        )

        self.worker.moveToThread(
            self.thread
        )

        # --------------------------------
        # Start worker
        # --------------------------------

        self.thread.started.connect(
            self.worker.run
        )

        # --------------------------------
        # Status
        # --------------------------------

        self.worker.status_changed.connect(
            self.status_changed
        )

        # --------------------------------
        # Completion
        # --------------------------------

        self.worker.finished.connect(
            self._task_finished
        )

        self.worker.error.connect(
            self._task_error
        )

        # --------------------------------
        # Stop thread
        # --------------------------------

        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.error.connect(
            self.thread.quit
        )

        # --------------------------------
        # Cleanup
        # --------------------------------

        self.thread.finished.connect(
            self.worker.deleteLater
        )

        self.thread.finished.connect(
            self.thread.deleteLater
        )

        self.thread.finished.connect(
            self._cleanup
        )

        self.thread.start()

    @Slot(bool)
    def _task_finished(
        self,
        success
    ):

        if success:

            self.status_changed.emit(
                "COMPLETED"
            )

        else:

            self.status_changed.emit(
                "FAILED"
            )

    @Slot(str)
    def _task_error(
        self,
        message
    ):

        print(
            f"[KAIRO BRIDGE ERROR] {message}"
        )

        self.status_changed.emit(
            "ERROR"
        )

    @Slot()
    def _cleanup(self):

        self.worker = None
        self.thread = None