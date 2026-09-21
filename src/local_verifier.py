import os
import time
from pathlib import Path

import pygetwindow as gw


class LocalVerifier:

    CHECK_TIMEOUT = 5.0
    POLL_INTERVAL = 0.25

    FILE_CHECK_TIMEOUT = 4.0
    FILE_POLL_INTERVAL = 0.25

    APP_ALIASES = {
        "chrome": [
            "google chrome",
            "chrome",
        ],
        "notepad": [
            "notepad",
        ],
        "visual studio code": [
            "visual studio code",
            "vs code",
            "code",
        ],
        "explorer": [
            "file explorer",
            "explorer",
        ],
        "calculator": [
            "calculator",
        ],
        "settings": [
            "settings",
        ],
        "paint": [
            "paint",
        ],
    }

    def _active_window_title(self):

        try:

            window = gw.getActiveWindow()

            if window is None:
                return ""

            title = window.title

            if title is None:
                return ""

            return title.strip()

        except Exception:

            return ""

    def _normalise(self, text):

        if not text:
            return ""

        return " ".join(
            text.lower().split()
        )

    def _find_expected_app(self, expected):

        if not expected:
            return None

        expected_normalised = (
            self._normalise(expected)
        )

        for app_name, aliases in self.APP_ALIASES.items():

            for alias in aliases:

                alias_normalised = (
                    self._normalise(alias)
                )

                if (
                    alias_normalised
                    in expected_normalised
                ):

                    return app_name

        return None

    def _window_matches_app(
        self,
        window_title,
        app_name
    ):

        title = self._normalise(
            window_title
        )

        if not title:
            return False

        aliases = self.APP_ALIASES.get(
            app_name,
            []
        )

        for alias in aliases:

            alias_normalised = (
                self._normalise(alias)
            )

            if alias_normalised in title:

                return True

        return False

    # =========================================================
    # General local checkpoint
    # =========================================================

    def should_check(
        self,
        action,
        last_typed
    ):
        """
        Perform an active-window check when an Enter press
        follows typed text.
        """

        if action.action != "press":
            return False

        if not action.key:
            return False

        if action.key.lower() != "enter":
            return False

        if not last_typed:
            return False

        return True

    def check_active_app(
        self,
        expected=None,
        last_typed=None
    ):
        """
        Returns:

            SUCCESS
                A deterministic application-state check passed.

            FAILED
                A deterministic application-state check failed.

            UNCERTAIN
                The local verifier cannot reliably determine
                the requested state.
        """

        expected_app = (
            self._find_expected_app(
                expected
            )
        )

        # --------------------------------
        # No deterministic application
        # check is available.
        # --------------------------------

        if expected_app is None:

            return {
                "status": "UNCERTAIN",
                "reason": (
                    "Local verifier cannot "
                    "deterministically verify "
                    f"expected state: {expected}"
                ),
                "active_window": (
                    self._active_window_title()
                ),
            }

        # --------------------------------
        # Wait for application to appear.
        # --------------------------------

        deadline = (
            time.monotonic()
            + self.CHECK_TIMEOUT
        )

        last_window = ""

        while time.monotonic() < deadline:

            last_window = (
                self._active_window_title()
            )

            if self._window_matches_app(
                last_window,
                expected_app
            ):

                return {
                    "status": "SUCCESS",
                    "reason": (
                        f"Expected application "
                        f"is active: {expected_app}"
                    ),
                    "active_window": last_window,
                }

            time.sleep(
                self.POLL_INTERVAL
            )

        # --------------------------------
        # Application didn't become active.
        # --------------------------------

        return {
            "status": "FAILED",
            "reason": (
                "Expected application is not active. "
                f"Current window: {last_window}"
            ),
            "active_window": last_window,
        }

    # =========================================================
    # File-save detection
    # =========================================================

    def is_save_checkpoint(
        self,
        action,
        last_typed
    ):
        """
        Determine whether this action represents the final
        Enter press of a save sequence.

        Example:

            type("kkl")
            press("enter")
            expected = "File is saved as kkl"
        """

        if action.action != "press":
            return False

        if not action.key:
            return False

        if action.key.lower() != "enter":
            return False

        if not last_typed:
            return False

        expected = (
            self._normalise(
                action.expected
            )
        )

        return (
            "saved as" in expected
            or "file is saved" in expected
            or "file saved" in expected
        )

    # =========================================================
    # Candidate file locations
    # =========================================================

    def _candidate_save_locations(
        self,
        filename
    ):
        """
        Return common Windows locations where a user-created
        file is likely to have been saved.
        """

        if not filename:
            return []

        filename = (
            str(filename)
            .strip()
            .strip('"')
        )

        user_profile = Path(
            os.environ.get(
                "USERPROFILE",
                ""
            )
        )

        locations = [
            user_profile / "Desktop",
            user_profile / "Documents",
            user_profile / "Downloads",
        ]

        candidates = []

        # Exact filename requested.
        for location in locations:

            candidates.append(
                location / filename
            )

        # Common Notepad .txt case.
        if not Path(filename).suffix:

            for location in locations:

                candidates.append(
                    location / f"{filename}.txt"
                )

        return candidates

    # =========================================================
    # Find saved file
    # =========================================================

    def find_saved_file(
        self,
        filename,
        started_at=None
    ):
        """
        Search common Windows save locations.

        If started_at is supplied, ignore files whose
        modification time predates the current task.
        """

        if not filename:
            return None

        candidates = (
            self._candidate_save_locations(
                filename
            )
        )

        deadline = (
            time.monotonic()
            + self.FILE_CHECK_TIMEOUT
        )

        while time.monotonic() < deadline:

            for path in candidates:

                try:

                    if not path.is_file():
                        continue

                    stat = path.stat()

                    # Ignore empty files.
                    if stat.st_size <= 0:
                        continue

                    # Ignore files that were not modified
                    # during this task.
                    if (
                        started_at is not None
                        and stat.st_mtime < started_at
                    ):
                        continue

                    return path

                except OSError:

                    continue

            time.sleep(
                self.FILE_POLL_INTERVAL
            )

        return None

    # =========================================================
    # Verify saved file
    # =========================================================

    def check_saved_file(
        self,
        filename,
        started_at=None
    ):
        """
        Deterministically verify that a saved file exists
        and contains data.
        """

        path = self.find_saved_file(
            filename=filename,
            started_at=started_at
        )

        if path is None:

            return {
                "status": "FAILED",
                "reason": (
                    f"File '{filename}' was not found "
                    "in the checked Windows save locations."
                ),
                "file_path": None,
            }

        try:

            file_size = path.stat().st_size

        except OSError:

            return {
                "status": "UNCERTAIN",
                "reason": (
                    f"File '{filename}' appeared, "
                    "but its metadata could not be read."
                ),
                "file_path": str(path),
            }

        return {
            "status": "SUCCESS",
            "reason": (
                f"File '{filename}' exists and contains "
                f"{file_size} bytes: {path}"
            ),
            "file_path": str(path),
            "size_bytes": file_size,
        }