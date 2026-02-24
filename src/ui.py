"""Rich TUI components for Pomobash timer"""

import shutil
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich.prompt import Prompt, IntPrompt, Confirm

from .models import Task, TaskStatus, PomodoroSession
from .timer import PomodoroTimer, TimerState
from .config import THEME, TIMER_DURATIONS, BREAK_DURATIONS

# Large digit font (height 5) - each digit is a list of 5 strings
DIGITS_SMALL = {
    "0": ["┌─┐", "│ │", "│ │", "│ │", "└─┘"],
    "1": [" ┐ ", " │ ", " │ ", " │ ", " ┘ "],
    "2": ["┌─┐", "  │", "┌─┘", "│  ", "└─┘"],
    "3": ["┌─┐", "  │", " ─┤", "  │", "└─┘"],
    "4": ["┐ ┐", "│ │", "└─┤", "  │", "  ┘"],
    "5": ["┌─┐", "│  ", "└─┐", "  │", "└─┘"],
    "6": ["┌─┐", "│  ", "├─┐", "│ │", "└─┘"],
    "7": ["┌─┐", "  │", "  │", "  │", "  ┘"],
    "8": ["┌─┐", "│ │", "├─┤", "│ │", "└─┘"],
    "9": ["┌─┐", "│ │", "└─┤", "  │", "└─┘"],
    ":": ["   ", " ● ", "   ", " ● ", "   "],
}

# Large digit font (height 7) for bigger terminals
DIGITS_LARGE = {
    "0": ["╔═══╗", "║   ║", "║   ║", "║   ║", "║   ║", "║   ║", "╚═══╝"],
    "1": ["  ╗  ", "  ║  ", "  ║  ", "  ║  ", "  ║  ", "  ║  ", "  ╝  "],
    "2": ["╔═══╗", "    ║", "    ║", "╔═══╝", "║    ", "║    ", "╚═══╝"],
    "3": ["╔═══╗", "    ║", "    ║", " ═══╣", "    ║", "    ║", "╚═══╝"],
    "4": ["╗   ╗", "║   ║", "║   ║", "╚═══╣", "    ║", "    ║", "    ╝"],
    "5": ["╔═══╗", "║    ", "║    ", "╚═══╗", "    ║", "    ║", "╚═══╝"],
    "6": ["╔═══╗", "║    ", "║    ", "╠═══╗", "║   ║", "║   ║", "╚═══╝"],
    "7": ["╔═══╗", "    ║", "    ║", "    ║", "    ║", "    ║", "    ╝"],
    "8": ["╔═══╗", "║   ║", "║   ║", "╠═══╣", "║   ║", "║   ║", "╚═══╝"],
    "9": ["╔═══╗", "║   ║", "║   ║", "╚═══╣", "    ║", "    ║", "╚═══╝"],
    ":": ["     ", "  ●  ", "     ", "     ", "     ", "  ●  ", "     "],
}


def render_big_time(time_str: str, terminal_width: int) -> str:
    """Render time string (MM:SS) as large ASCII art, scaled to terminal width."""
    # Choose font based on terminal width
    if terminal_width >= 60:
        digits = DIGITS_LARGE
    else:
        digits = DIGITS_SMALL

    height = len(next(iter(digits.values())))
    lines = [""] * height

    for ch in time_str:
        glyph = digits.get(ch, digits["0"])
        for row in range(height):
            lines[row] += glyph[row] + " "

    return "\n".join(lines)


class PomodoroUI:
    """Rich TUI interface for Pomobash timer"""

    def __init__(self):
        self.console = Console()

    def clear(self):
        """Clear the console"""
        self.console.clear()

    def print(self, *args, **kwargs):
        """Print to console"""
        self.console.print(*args, **kwargs)

    def _get_terminal_width(self) -> int:
        """Get current terminal width."""
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def render_timer_display(
        self,
        timer: PomodoroTimer,
        task: Optional[Task] = None,
        is_break: bool = False
    ) -> Panel:
        """
        Render the timer display with large ASCII art digits and progress bar.
        The display scales with the terminal window size.

        Args:
            timer: PomodoroTimer instance
            task: Current task (optional)
            is_break: Whether this is a break timer

        Returns:
            Rich Panel with timer display
        """
        term_width = self._get_terminal_width()
        # Timer type and task info
        timer_type = "BREAK TIME" if is_break else "POMOBASH TIMER"
        color = THEME["break"] if is_break else THEME["timer"]

        content = []

        # Title
        title = Text(timer_type, style=f"bold {color}", justify="center")
        content.append(title)
        content.append("")

        # Task info (if not a break)
        if task and not is_break:
            task_text = Text(f"Task: {task.title}", style=THEME["task"], justify="center")
            content.append(task_text)

            # Progress info
            pomodoro_text = f"{task.pomodoros_completed}"
            if task.estimated_pomodoros:
                pomodoro_text += f"/{task.estimated_pomodoros}"
            progress_text = Text(
                f"Progress: {task.completion_percentage}% | Pomodoros: {pomodoro_text}",
                style=THEME["info"],
                justify="center"
            )
            content.append(progress_text)
            content.append("")

        # Large ASCII art time
        remaining = timer.get_remaining_time_formatted()
        big_time = render_big_time(remaining, term_width)
        big_time_text = Text(big_time, style=f"bold {color}", justify="center")
        content.append(big_time_text)
        content.append("")

        # Progress bar - scale width to terminal
        progress = timer.get_progress()
        bar_width = max(20, min(term_width - 20, 60))
        filled = int(progress * bar_width)
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty
        bar_text = Text(f"{bar}  {int(progress * 100)}%", style=THEME["progress"], justify="center")
        content.append(bar_text)
        content.append("")

        # State indicator
        if timer.is_paused():
            state_text = Text("⏸  PAUSED", style=THEME["warning"], justify="center")
            content.append(state_text)
            content.append("")

        # Controls
        controls = "[P]ause  [R]estart  [S]top  [Q]uit"
        if timer.is_paused():
            controls = "[P]Resume  [R]estart  [S]top  [Q]uit"
        content.append(Text(controls, style="dim", justify="center"))

        # Combine all content
        panel_content = "\n".join(str(item) for item in content)

        return Panel(
            Align.center(panel_content),
            border_style=color,
            padding=(1, 2)
        )

    def render_task_list(self, tasks: List[Task]) -> Table:
        """
        Render task list as a table

        Args:
            tasks: List of tasks

        Returns:
            Rich Table with tasks
        """
        table = Table(title="Today's Tasks", show_header=True, header_style="bold")

        table.add_column("#", style="dim", width=3)
        table.add_column("Task", style=THEME["task"], no_wrap=False)
        table.add_column("Status", width=12)
        table.add_column("Progress", width=15)
        table.add_column("Pomodoros", width=10)

        for i, task in enumerate(tasks, 1):
            # Status with color
            status_text = task.status.value.replace("_", " ").title()
            if task.status == TaskStatus.COMPLETED:
                status_style = THEME["completed"]
                status_icon = "✓"
            elif task.status == TaskStatus.IN_PROGRESS:
                status_style = THEME["progress"]
                status_icon = "▶"
            else:
                status_style = "white"
                status_icon = "○"

            status = f"[{status_style}]{status_icon} {status_text}[/{status_style}]"

            # Progress bar
            progress = task.completion_percentage
            bar_width = 8
            filled = int((progress / 100) * bar_width)
            empty = bar_width - filled
            progress_bar = f"[{THEME['progress']}]{'█' * filled}[/]{'░' * empty} {progress}%"

            # Pomodoros
            pomodoro_text = str(task.pomodoros_completed)
            if task.estimated_pomodoros:
                pomodoro_text += f"/{task.estimated_pomodoros}"

            table.add_row(
                str(i),
                task.title[:40] + "..." if len(task.title) > 40 else task.title,
                status,
                progress_bar,
                pomodoro_text
            )

        if not tasks:
            table.add_row("", "No tasks yet", "", "", "")

        return table

    def render_session_summary(self, sessions: List[PomodoroSession]) -> Panel:
        """
        Render today's session summary

        Args:
            sessions: List of today's sessions

        Returns:
            Rich Panel with summary
        """
        if not sessions:
            return Panel("No sessions today yet", title="Today's Sessions", border_style=THEME["info"])

        work_sessions = [s for s in sessions if not s.is_break and s.completed]
        break_sessions = [s for s in sessions if s.is_break and s.completed]

        total_work_minutes = sum(s.duration_minutes for s in work_sessions)
        total_break_minutes = sum(s.duration_minutes for s in break_sessions)

        hours = total_work_minutes // 60
        minutes = total_work_minutes % 60

        summary_lines = [
            f"[{THEME['completed']}]Completed Pomodoros:[/] {len(work_sessions)}",
            f"[{THEME['timer']}]Total Work Time:[/] {hours}h {minutes}m",
            f"[{THEME['break']}]Total Break Time:[/] {total_break_minutes}m",
        ]

        content = "\n".join(summary_lines)

        return Panel(content, title="Today's Progress", border_style=THEME["info"])

    def show_main_menu(self) -> str:
        """
        Show main menu and get user choice

        Returns:
            Selected action
        """
        self.print("\n[bold]POMOBASH TIMER[/bold]\n")
        self.print("[1] Start Timer")
        self.print("[2] Manage Tasks")
        self.print("[3] View Stats")
        self.print("[4] Exit")

        choice = Prompt.ask("\nChoose an option", choices=["1", "2", "3", "4"], default="1")
        return choice

    def show_task_menu(self) -> str:
        """
        Show task management menu

        Returns:
            Selected action
        """
        self.print("\n[bold]TASK MANAGEMENT[/bold]\n")
        self.print("[1] List all tasks")
        self.print("[2] Add new task")
        self.print("[3] Update task progress")
        self.print("[4] Mark task complete")
        self.print("[5] Delete task")
        self.print("[0] Back")

        choice = Prompt.ask("\nChoose an option", choices=["0", "1", "2", "3", "4", "5"], default="1")
        return choice

    def prompt_timer_duration(self) -> int:
        """
        Prompt user to select timer duration

        Returns:
            Duration in minutes
        """
        self.print("\n[bold]Select Timer Duration:[/bold]")
        self.print(f"[1] Short ({TIMER_DURATIONS['short']} minutes)")
        self.print(f"[2] Medium ({TIMER_DURATIONS['medium']} minutes)")
        self.print(f"[3] Long ({TIMER_DURATIONS['long']} minutes)")

        choice = Prompt.ask("Duration", choices=["1", "2", "3"], default="1")

        duration_map = {
            "1": TIMER_DURATIONS["short"],
            "2": TIMER_DURATIONS["medium"],
            "3": TIMER_DURATIONS["long"]
        }

        return duration_map[choice]

    def prompt_break_duration(self) -> int:
        """
        Prompt user to select break duration

        Returns:
            Duration in minutes
        """
        self.print("\n[bold]Select Break Duration:[/bold]")
        self.print(f"[1] Short ({BREAK_DURATIONS['short']} minutes)")
        self.print(f"[2] Medium ({BREAK_DURATIONS['medium']} minutes)")
        self.print(f"[3] Long ({BREAK_DURATIONS['long']} minutes)")

        choice = Prompt.ask("Break", choices=["1", "2", "3"], default="1")

        duration_map = {
            "1": BREAK_DURATIONS["short"],
            "2": BREAK_DURATIONS["medium"],
            "3": BREAK_DURATIONS["long"]
        }

        return duration_map[choice]

    def prompt_task_selection(self, tasks: List[Task]) -> Optional[int]:
        """
        Prompt user to select a task from list

        Args:
            tasks: List of available tasks

        Returns:
            Task index (0-based) or None for new task
        """
        if not tasks:
            return None

        self.print("\n[bold]Select a task:[/bold]")
        for i, task in enumerate(tasks, 1):
            status = "✓" if task.status == TaskStatus.COMPLETED else "▶" if task.status == TaskStatus.IN_PROGRESS else "○"
            self.print(f"[{i}] {status} {task.title} ({task.completion_percentage}%)")

        self.print("[0] Create new task")

        max_choice = len(tasks)
        choice = IntPrompt.ask("Task", default=1)

        if choice == 0:
            return None
        elif 1 <= choice <= max_choice:
            return choice - 1
        else:
            self.print(f"[{THEME['warning']}]Invalid choice[/]")
            return None

    def prompt_task_creation(self) -> dict:
        """
        Prompt user to create a new task

        Returns:
            Dictionary with task details
        """
        self.print("\n[bold]Create New Task[/bold]")

        title = Prompt.ask("Task title")
        description = Prompt.ask("Description (optional)", default="")
        estimated = Prompt.ask("Estimated pomodoros (optional)", default="")

        estimated_int = None
        if estimated and estimated.isdigit():
            estimated_int = int(estimated)

        return {
            "title": title,
            "description": description if description else None,
            "estimated_pomodoros": estimated_int
        }

    def prompt_completion_percentage(self, current: int) -> int:
        """
        Prompt user for completion percentage

        Args:
            current: Current percentage

        Returns:
            New percentage (0-100)
        """
        self.print(f"\nCurrent progress: {current}%")
        percentage = IntPrompt.ask(
            "New percentage (0-100)",
            default=current
        )

        return max(0, min(100, percentage))

    def show_notification(self, message: str, style: str = "info") -> None:
        """
        Show a notification message

        Args:
            message: Message to display
            style: Style (info, warning, completed)
        """
        color = THEME.get(style, THEME["info"])
        self.print(f"\n[{color}]{message}[/{color}]")

    def confirm(self, message: str) -> bool:
        """
        Show confirmation prompt

        Args:
            message: Confirmation message

        Returns:
            True if confirmed, False otherwise
        """
        return Confirm.ask(message)
