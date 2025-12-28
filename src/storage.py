"""JSON persistence layer for Pomobash timer data"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from json.decoder import JSONDecodeError
from pydantic import ValidationError

from .models import (
    DailyState,
    Task,
    PomodoroSession,
    CompletedTasksLog,
    SessionsLog,
    TaskStatus
)
from .config import (
    DATA_DIR,
    TASKS_FILE,
    COMPLETED_FILE,
    SESSIONS_FILE
)


def ensure_data_directory() -> None:
    """Create data directory if it doesn't exist"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def backup_corrupted_file(file_path: Path) -> None:
    """Backup a corrupted file with timestamp"""
    if file_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".corrupted_{timestamp}")
        shutil.copy2(file_path, backup_path)
        print(f"Warning: Corrupted file backed up to {backup_path}")


def atomic_write(file_path: Path, data: str) -> None:
    """Write data to file atomically using temp file + rename"""
    ensure_data_directory()
    temp_file = file_path.with_suffix('.tmp')
    temp_file.write_text(data)
    temp_file.replace(file_path)


def load_daily_state() -> DailyState:
    """
    Load daily state from tasks.json
    Returns fresh state if file doesn't exist or date doesn't match today
    """
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        if TASKS_FILE.exists():
            data = json.loads(TASKS_FILE.read_text())

            # Check if date matches today
            if data.get("date") == today:
                # Parse tasks with proper enum handling
                if "current_task" in data and data["current_task"]:
                    data["current_task"]["status"] = TaskStatus(data["current_task"]["status"])

                for task in data.get("tasks", []):
                    task["status"] = TaskStatus(task["status"])

                return DailyState.model_validate(data)
            else:
                # Archive yesterday's data and start fresh
                archive_old_tasks(data)
                return DailyState(date=today)

        return DailyState(date=today)

    except (JSONDecodeError, ValidationError, KeyError, ValueError) as e:
        print(f"Error loading daily state: {e}")
        backup_corrupted_file(TASKS_FILE)
        return DailyState(date=today)


def save_daily_state(state: DailyState) -> None:
    """Save daily state to tasks.json with atomic write"""
    data = state.model_dump(mode='json')

    # Convert enum values to strings
    if data.get("current_task"):
        data["current_task"]["status"] = data["current_task"]["status"].value if hasattr(data["current_task"]["status"], "value") else data["current_task"]["status"]

    for task in data.get("tasks", []):
        task["status"] = task["status"].value if hasattr(task["status"], "value") else task["status"]

    json_data = json.dumps(data, indent=2, default=str)
    atomic_write(TASKS_FILE, json_data)


def archive_old_tasks(old_data: dict) -> None:
    """Archive completed tasks from previous day"""
    try:
        completed_tasks = []

        # Check current task
        if old_data.get("current_task") and old_data["current_task"].get("status") == "completed":
            completed_tasks.append(old_data["current_task"])

        # Check task list
        for task in old_data.get("tasks", []):
            if task.get("status") == "completed":
                completed_tasks.append(task)

        if completed_tasks:
            save_completed_tasks(completed_tasks)

    except Exception as e:
        print(f"Error archiving old tasks: {e}")


def load_completed_tasks() -> List[Task]:
    """Load all completed tasks from completed.json"""
    try:
        if COMPLETED_FILE.exists():
            data = json.loads(COMPLETED_FILE.read_text())

            # Convert status strings to enums
            for task in data.get("tasks", []):
                task["status"] = TaskStatus(task["status"])

            log = CompletedTasksLog.model_validate(data)
            return log.tasks

        return []

    except (JSONDecodeError, ValidationError, KeyError, ValueError) as e:
        print(f"Error loading completed tasks: {e}")
        backup_corrupted_file(COMPLETED_FILE)
        return []


def save_completed_tasks(tasks: List[Task] | List[dict]) -> None:
    """Append completed tasks to completed.json"""
    existing_tasks = load_completed_tasks()

    # Convert dict to Task if needed
    new_tasks = []
    for task in tasks:
        if isinstance(task, dict):
            task["status"] = TaskStatus(task["status"]) if isinstance(task["status"], str) else task["status"]
            new_tasks.append(Task.model_validate(task))
        else:
            new_tasks.append(task)

    existing_tasks.extend(new_tasks)

    log = CompletedTasksLog(tasks=existing_tasks)
    data = log.model_dump(mode='json')

    # Convert enum values
    for task in data["tasks"]:
        task["status"] = task["status"].value if hasattr(task["status"], "value") else task["status"]

    json_data = json.dumps(data, indent=2, default=str)
    atomic_write(COMPLETED_FILE, json_data)


def load_sessions() -> List[PomodoroSession]:
    """Load all Pomodoro sessions from sessions.json"""
    try:
        if SESSIONS_FILE.exists():
            data = json.loads(SESSIONS_FILE.read_text())
            log = SessionsLog.model_validate(data)
            return log.sessions

        return []

    except (JSONDecodeError, ValidationError) as e:
        print(f"Error loading sessions: {e}")
        backup_corrupted_file(SESSIONS_FILE)
        return []


def save_session(session: PomodoroSession) -> None:
    """Append a Pomodoro session to sessions.json"""
    existing_sessions = load_sessions()
    existing_sessions.append(session)

    log = SessionsLog(sessions=existing_sessions)
    data = log.model_dump(mode='json')
    json_data = json.dumps(data, indent=2, default=str)
    atomic_write(SESSIONS_FILE, json_data)


def get_today_sessions() -> List[PomodoroSession]:
    """Get sessions for today only"""
    all_sessions = load_sessions()
    today = datetime.now().strftime("%Y-%m-%d")

    return [
        session for session in all_sessions
        if session.start_time.strftime("%Y-%m-%d") == today
    ]
