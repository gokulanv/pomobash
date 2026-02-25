"""CLI interface and main application orchestration"""

import sys
import time
import subprocess
import select
import tty
import termios
from datetime import datetime
from typing import Optional

import click
from rich.live import Live

from .models import PomodoroSession, Task, TaskStatus
from .timer import PomodoroTimer, TimerState
from .ui import PomodoroUI
from .storage import (
    load_daily_state,
    save_daily_state,
    save_session,
    get_today_sessions,
    ensure_data_directory
)
from .tasks import (
    create_task,
    list_tasks,
    get_current_task,
    set_current_task,
    update_task_progress,
    mark_task_completed,
    delete_task,
    increment_pomodoro_count,
    get_task_summary
)
from .config import COMPLETION_SOUND


# Global UI instance
ui = PomodoroUI()


def play_completion_sound():
    """Play macOS completion sound"""
    try:
        subprocess.run(["afplay", COMPLETION_SOUND], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass  # Ignore if sound fails to play


def get_key_non_blocking():
    """
    Get keyboard input without blocking (Unix/macOS)
    Returns None if no key is pressed
    """
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1).lower()
    return None


def handle_timer_completion(
    task: Optional[Task],
    duration_minutes: int,
    is_break: bool = False
) -> None:
    """
    Handle timer completion

    Args:
        task: Current task (if not a break)
        duration_minutes: Timer duration
        is_break: Whether this was a break timer
    """
    # Play sound
    play_completion_sound()

    # Show notification
    if is_break:
        ui.show_notification("Break complete! Time to focus.", "completed")
    else:
        ui.show_notification("Pomobash complete! Great work!", "completed")

        # Increment pomodoro count for task
        if task:
            increment_pomodoro_count(task.id)

            # Prompt for progress update
            if ui.confirm("\nUpdate task progress?"):
                new_percentage = ui.prompt_completion_percentage(task.completion_percentage)
                update_task_progress(task.id, new_percentage)

                # Check if task should be marked complete
                if new_percentage == 100:
                    if ui.confirm("Mark task as completed?"):
                        mark_task_completed(task.id)
                        ui.show_notification(f"Task '{task.title}' completed!", "completed")


def run_timer_loop(
    timer: PomodoroTimer,
    task: Optional[Task],
    is_break: bool = False
) -> bool:
    """
    Run the timer loop with live display and keyboard controls

    Args:
        timer: PomodoroTimer instance
        task: Current task
        is_break: Whether this is a break timer

    Returns:
        True if timer completed, False if interrupted
    """
    timer.start()
    completed = False

    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Set terminal to raw mode for non-blocking input
        tty.setcbreak(sys.stdin.fileno())

        with Live(ui.render_timer_display(timer, task, is_break), refresh_per_second=2) as live:
            while not timer.is_finished():
                # Check for keyboard input
                key = get_key_non_blocking()

                if key:
                    if key == 'p':
                        # Pause/Resume
                        if timer.is_running():
                            timer.pause()
                        elif timer.is_paused():
                            timer.resume()
                    elif key == 'r':
                        # Restart
                        timer.restart()
                    elif key == 's':
                        # Stop
                        timer.stop()
                        break
                    elif key == 'q':
                        # Quit
                        timer.stop()
                        break

                # Update timer
                timer.tick()

                # Update display
                live.update(ui.render_timer_display(timer, task, is_break))

                # Sleep briefly
                time.sleep(0.5)

            completed = timer.is_finished()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        ui.print("\n\nTimer interrupted")
        return False
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    return completed


def create_session_record(
    task: Optional[Task],
    duration_minutes: int,
    completed: bool,
    is_break: bool = False
) -> PomodoroSession:
    """
    Create and save a session record

    Args:
        task: Task associated with session
        duration_minutes: Session duration
        completed: Whether session was completed
        is_break: Whether this was a break

    Returns:
        PomodoroSession instance
    """
    session = PomodoroSession(
        task_id=task.id if task else None,
        task_title=task.title if task else ("Break" if is_break else "Pomodoro"),
        duration_minutes=duration_minutes,
        completed=completed,
        interrupted=not completed,
        is_break=is_break,
        end_time=datetime.now() if completed else None
    )

    save_session(session)
    return session


def start_timer_flow(duration: Optional[str] = None, task_id: Optional[str] = None):
    """
    Start a Pomobash timer flow (separated for reuse)
    """
    ui.clear()

    # Get or create task
    current_task = None

    if task_id:
        # Use specified task ID
        from .tasks import get_task_by_id
        current_task = get_task_by_id(task_id)
        if not current_task:
            ui.show_notification(f"Task {task_id} not found", "warning")
            return
        set_current_task(task_id)
    else:
        # Check for current task
        current_task = get_current_task()

        if current_task:
            # Ask if user wants to continue
            if not ui.confirm(f"\nContinue with current task: {current_task.title}?"):
                current_task = None

        # Select or create task
        if not current_task:
            tasks = list_tasks()
            if tasks:
                task_idx = ui.prompt_task_selection(tasks)
                if task_idx == -1:          # user cancelled
                    return
                elif task_idx is not None:  # selected existing task
                    current_task = tasks[task_idx]
                    set_current_task(current_task.id)
                # task_idx None → fall through to create new task

            if current_task is None:
                task_data = ui.prompt_task_creation()
                if task_data is not None:
                    current_task = create_task(**task_data)
                    set_current_task(current_task.id)
                # else: proceed with no task

    # Get timer duration
    if duration:
        duration_minutes = int(duration)
    else:
        duration_minutes = ui.prompt_timer_duration()
        if duration_minutes is None:
            return

    # Create and run timer
    ui.clear()
    ui.show_notification(f"Starting {duration_minutes}-minute Pomobash", "timer")
    if current_task:
        ui.print(f"Task: [bold]{current_task.title}[/bold]")
    ui.print("\n")

    timer = PomodoroTimer(duration_minutes)
    completed = run_timer_loop(timer, current_task, is_break=False)

    # Save session
    create_session_record(current_task, duration_minutes, completed, is_break=False)

    # Handle completion
    if completed:
        handle_timer_completion(current_task, duration_minutes, is_break=False)

        # Offer break
        if ui.confirm("\nTake a break?"):
            break_duration = ui.prompt_break_duration()
            if break_duration is not None:
                ui.clear()
                ui.show_notification(f"Starting {break_duration}-minute break", "break")

                break_timer = PomodoroTimer(break_duration)
                break_completed = run_timer_loop(break_timer, None, is_break=True)

                # Save break session
                create_session_record(None, break_duration, break_completed, is_break=True)

                if break_completed:
                    handle_timer_completion(None, break_duration, is_break=True)


def manage_tasks_flow():
    """
    Task management flow (separated for reuse)
    """
    while True:
        ui.clear()

        # Show task list
        all_tasks = list_tasks()
        table = ui.render_task_list(all_tasks)
        ui.print(table)

        # Show menu
        choice = ui.show_task_menu()

        if choice == "0":
            break
        elif choice == "1":
            # List already shown above
            input("\nPress Enter to continue...")
        elif choice == "2":
            # Add new task
            task_data = ui.prompt_task_creation()
            if task_data is not None:
                task = create_task(**task_data)
                ui.show_notification(f"Task '{task.title}' created!", "completed")
                time.sleep(1)
        elif choice == "3":
            # Update task progress
            if not all_tasks:
                ui.show_notification("No tasks available", "warning")
                time.sleep(1)
                continue

            task_idx = ui.prompt_task_selection(all_tasks)
            if task_idx is not None and task_idx >= 0:
                task = all_tasks[task_idx]
                new_percentage = ui.prompt_completion_percentage(task.completion_percentage)
                update_task_progress(task.id, new_percentage)
                ui.show_notification("Progress updated!", "completed")
                time.sleep(1)
        elif choice == "4":
            # Mark task complete
            if not all_tasks:
                ui.show_notification("No tasks available", "warning")
                time.sleep(1)
                continue

            task_idx = ui.prompt_task_selection(all_tasks)
            if task_idx is not None and task_idx >= 0:
                task = all_tasks[task_idx]
                if ui.confirm(f"Mark '{task.title}' as completed?"):
                    mark_task_completed(task.id)
                    ui.show_notification("Task completed!", "completed")
                    time.sleep(1)
        elif choice == "5":
            # Delete task
            if not all_tasks:
                ui.show_notification("No tasks available", "warning")
                time.sleep(1)
                continue

            task_idx = ui.prompt_task_selection(all_tasks)
            if task_idx is not None and task_idx >= 0:
                task = all_tasks[task_idx]
                if ui.confirm(f"Delete '{task.title}'?"):
                    delete_task(task.id)
                    ui.show_notification("Task deleted!", "completed")
                    time.sleep(1)


def show_stats_flow():
    """
    Statistics display flow (separated for reuse)
    """
    ui.clear()

    # Today's sessions
    sessions = get_today_sessions()
    summary_panel = ui.render_session_summary(sessions)
    ui.print(summary_panel)

    # Task summary
    task_summary = get_task_summary()
    ui.print("\n[bold]Task Summary[/bold]")
    ui.print(f"Total tasks: {task_summary['total_tasks']}")
    ui.print(f"  Todo: {task_summary['todo']}")
    ui.print(f"  In Progress: {task_summary['in_progress']}")
    ui.print(f"  Completed: {task_summary['completed']}")
    ui.print(f"Total pomodoros: {task_summary['total_pomodoros']}")

    # Recent sessions
    if sessions:
        ui.print("\n[bold]Recent Sessions[/bold]")
        for session in sessions[-5:]:  # Last 5 sessions
            time_str = session.start_time.strftime("%H:%M")
            status = "✓" if session.completed else "✗"
            session_type = "Break" if session.is_break else "Work"
            ui.print(f"  {time_str} - {session.task_title} ({session.duration_minutes}m) {status} [{session_type}]")

    input("\nPress Enter to continue...")


@click.group()
def cli():
    """Pomobash Timer CLI - Focus and track your work"""
    ensure_data_directory()


@cli.command()
@click.option('--duration', type=click.Choice(['20', '40', '60']), help='Timer duration in minutes')
@click.option('--task-id', type=str, help='Task ID to work on')
def start(duration: Optional[str], task_id: Optional[str]):
    """Start a Pomobash timer"""
    start_timer_flow(duration, task_id)


@cli.command()
def tasks():
    """Manage tasks"""
    manage_tasks_flow()


@cli.command()
def stats():
    """Show productivity statistics"""
    show_stats_flow()


@cli.command()
def reset():
    """Reset daily tasks (start fresh)"""
    if ui.confirm("This will clear today's tasks. Continue?"):
        from .storage import TASKS_FILE
        if TASKS_FILE.exists():
            TASKS_FILE.unlink()
        ui.show_notification("Daily tasks reset!", "completed")


@cli.command()
def interactive():
    """Start interactive mode with main menu"""
    try:
        while True:
            ui.clear()

            # Show today's progress
            sessions = get_today_sessions()
            if sessions:
                summary_panel = ui.render_session_summary(sessions)
                ui.print(summary_panel)
                ui.print()

            # Show tasks
            all_tasks = list_tasks()
            if all_tasks:
                table = ui.render_task_list(all_tasks[:5])  # Show top 5
                ui.print(table)

            # Show main menu
            choice = ui.show_main_menu()

            if choice == "1":
                # Start timer - call the flow function directly
                start_timer_flow()
            elif choice == "2":
                # Manage tasks - call the flow function directly
                manage_tasks_flow()
            elif choice == "3":
                # View stats - call the flow function directly
                show_stats_flow()
            elif choice == "4":
                # Exit
                ui.show_notification("Goodbye!", "info")
                break
    except KeyboardInterrupt:
        ui.show_notification("\nGoodbye!", "info")


if __name__ == '__main__':
    cli()
