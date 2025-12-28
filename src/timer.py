"""Timer engine for Pomobash sessions"""

import time
from datetime import datetime
from enum import Enum
from typing import Optional, Callable


class TimerState(Enum):
    """Timer state machine states"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class PomodoroTimer:
    """
    Pomobash timer with tick-based countdown
    """

    def __init__(self, duration_minutes: int):
        """
        Initialize timer with duration in minutes

        Args:
            duration_minutes: Timer duration in minutes
        """
        self.duration_seconds = duration_minutes * 60
        self.remaining_seconds = self.duration_seconds
        self.state = TimerState.IDLE
        self.start_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.paused_elapsed = 0  # Total time spent paused

    def start(self) -> None:
        """Start the timer"""
        if self.state == TimerState.IDLE:
            self.state = TimerState.RUNNING
            self.start_time = datetime.now()

    def pause(self) -> None:
        """Pause the timer"""
        if self.state == TimerState.RUNNING:
            self.state = TimerState.PAUSED
            self.pause_time = datetime.now()

    def resume(self) -> None:
        """Resume a paused timer"""
        if self.state == TimerState.PAUSED and self.pause_time:
            pause_duration = (datetime.now() - self.pause_time).total_seconds()
            self.paused_elapsed += pause_duration
            self.state = TimerState.RUNNING
            self.pause_time = None

    def restart(self) -> None:
        """Restart the timer from the beginning"""
        self.remaining_seconds = self.duration_seconds
        self.state = TimerState.IDLE
        self.start_time = None
        self.pause_time = None
        self.paused_elapsed = 0
        self.start()

    def stop(self) -> None:
        """Stop the timer"""
        self.state = TimerState.IDLE
        self.remaining_seconds = self.duration_seconds
        self.start_time = None
        self.pause_time = None
        self.paused_elapsed = 0

    def tick(self) -> int:
        """
        Update timer state (call every second)

        Returns:
            Remaining seconds
        """
        if self.state == TimerState.RUNNING and self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds() - self.paused_elapsed
            self.remaining_seconds = max(0, self.duration_seconds - int(elapsed))

            if self.remaining_seconds == 0:
                self.state = TimerState.COMPLETED

        return self.remaining_seconds

    def is_running(self) -> bool:
        """Check if timer is currently running"""
        return self.state == TimerState.RUNNING

    def is_paused(self) -> bool:
        """Check if timer is paused"""
        return self.state == TimerState.PAUSED

    def is_finished(self) -> bool:
        """Check if timer has completed"""
        return self.state == TimerState.COMPLETED

    def get_progress(self) -> float:
        """
        Get timer progress as a fraction

        Returns:
            Progress from 0.0 (start) to 1.0 (complete)
        """
        if self.duration_seconds == 0:
            return 1.0

        return 1.0 - (self.remaining_seconds / self.duration_seconds)

    def get_elapsed_seconds(self) -> int:
        """Get elapsed time in seconds"""
        return self.duration_seconds - self.remaining_seconds

    def format_time(self, seconds: int) -> str:
        """
        Format seconds as MM:SS

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string (MM:SS)
        """
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def get_remaining_time_formatted(self) -> str:
        """Get remaining time formatted as MM:SS"""
        return self.format_time(self.remaining_seconds)

    def get_elapsed_time_formatted(self) -> str:
        """Get elapsed time formatted as MM:SS"""
        return self.format_time(self.get_elapsed_seconds())
