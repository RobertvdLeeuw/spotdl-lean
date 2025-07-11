"""
Minimal progress handler that removes all TUI functionality.
Replace the content of spotdl/download/progress_handler.py with this.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from spotdl.types.song import Song

__all__ = [
    "ProgressHandler",
    "SongTracker",
    "ProgressHandlerError",
]

logger = logging.getLogger(__name__)


class ProgressHandlerError(Exception):
    """
    Base class for all exceptions raised by ProgressHandler subclasses.
    """


class ProgressHandler:
    """
    Minimal progress handler without TUI components.
    """

    def __init__(
        self,
        simple_tui: bool = False,  # Keep for compatibility but ignore
        update_callback: Optional[Callable[[Any, str], None]] = None,
        web_ui: bool = False,
    ):
        """
        Initialize the minimal progress handler.

        ### Arguments
        - simple_tui: Ignored (kept for compatibility)
        - update_callback: A callback to call when progress updates occur
        - web_ui: Whether this is being used for web UI
        """
        self.songs: List[Song] = []
        self.song_count: int = 0
        self.overall_progress = 0
        self.overall_total = 100
        self.overall_completed_tasks = 0
        self.update_callback = update_callback
        self.web_ui = web_ui

    def add_song(self, song: Song) -> None:
        """
        Adds a song to the list of songs.

        ### Arguments
        - song: The song to add.
        """
        self.songs.append(song)
        self.set_song_count(len(self.songs))

    def set_songs(self, songs: List[Song]) -> None:
        """
        Sets the list of songs to be downloaded.

        ### Arguments
        - songs: The list of songs to download.
        """
        self.songs = songs
        self.set_song_count(len(songs))

    def set_song_count(self, count: int) -> None:
        """
        Set the number of songs to download.

        ### Arguments
        - count: The number of songs to download.
        """
        self.song_count = count
        self.overall_total = 100 * count

    def update_overall(self) -> None:
        """
        Update the overall progress (minimal implementation).
        """
        pass

    def get_new_tracker(self, song: Song) -> "SongTracker":
        """
        Get a new progress tracker.

        ### Arguments
        - song: The song to track.

        ### Returns
        - A new progress tracker.
        """
        return SongTracker(self, song)

    def close(self) -> None:
        """
        Close the progress handler (minimal implementation).
        """
        pass


class SongTracker:
    """
    Minimal song tracker without TUI components.
    """

    def __init__(self, parent: ProgressHandler, song: Song) -> None:
        """
        Initialize the minimal song tracker.

        ### Arguments
        - parent: The parent progress handler
        - song: The song to track
        """
        self.parent = parent
        self.song = song
        self.progress: int = 0
        self.old_progress: int = 0
        self.status = ""

    def update(self, message=""):
        """
        Called at every progress event.

        ### Arguments
        - message: The message to display.
        """
        old_message = self.status
        self.status = message
        delta = self.progress - self.old_progress

        # Update completion tracking
        if self.progress == 100 or message == "Error":
            self.parent.overall_completed_tasks += 1

        # Update overall progress
        if self.parent.song_count == self.parent.overall_completed_tasks:
            self.parent.overall_progress = self.parent.song_count * 100
        else:
            self.parent.overall_progress += delta

        self.parent.update_overall()
        self.old_progress = self.progress

        # Call update callback if provided
        if self.parent.update_callback:
            self.parent.update_callback(self, message)

        # Log progress for web UI if needed
        if self.parent.web_ui and old_message != self.status:
            logger.info("%s: %s", self.song.display_name, message)

    def notify_error(
        self, message: str, traceback: Exception, finish: bool = False
    ) -> None:
        """
        Logs an error message.

        ### Arguments
        - message: The message to log.
        - traceback: The traceback of the error.
        - finish: Whether to finish the task.
        """
        self.update("Error")
        if finish:
            self.progress = 100

        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.exception(message)
        else:
            logger.error("%s: %s", traceback.__class__.__name__, traceback)

    def notify_download_complete(self, status="Converting") -> None:
        """
        Notifies the progress handler that the song has been downloaded.

        ### Arguments
        - status: The status to display.
        """
        self.progress = 50
        self.update(status)

    def notify_conversion_complete(self, status="Embedding metadata") -> None:
        """
        Notifies the progress handler that the song has been converted.

        ### Arguments
        - status: The status to display.
        """
        self.progress = 95
        self.update(status)

    def notify_complete(self, status="Done") -> None:
        """
        Notifies the progress handler that the song has been downloaded and converted.

        ### Arguments
        - status: The status to display.
        """
        self.progress = 100
        self.update(status)

    def notify_download_skip(self, status="Skipped") -> None:
        """
        Notifies the progress handler that the song has been skipped.

        ### Arguments
        - status: The status to display.
        """
        self.progress = 100
        self.update(status)

    def ffmpeg_progress_hook(self, progress: int) -> None:
        """
        Updates the progress during ffmpeg conversion.

        ### Arguments
        - progress: The progress percentage.
        """
        self.progress = 50 + int(progress * 0.45)
        self.update("Converting")

    def yt_dlp_progress_hook(self, data: Dict[str, Any]) -> None:
        """
        Updates the progress during download.

        ### Arguments
        - data: Progress data from yt-dlp.
        """
        if data["status"] == "downloading":
            file_bytes = data.get("total_bytes")
            if file_bytes is None:
                file_bytes = data.get("total_bytes_estimate")

            downloaded_bytes = data.get("downloaded_bytes")
            if file_bytes and downloaded_bytes:
                self.progress = downloaded_bytes / file_bytes * 50
            else:
                self.progress = 50

            self.update("Downloading")
