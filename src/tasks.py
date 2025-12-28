"""Task management operations"""

from datetime import datetime
from typing import List, Optional

from .models import Task, TaskStatus, DailyState
from .storage import load_daily_state, save_daily_state, save_completed_tasks


def create_task(
    title: str,
    description: Optional[str] = None,
    estimated_pomodoros: Optional[int] = None
) -> Task:
    """
    Create a new task

    Args:
        title: Task title
        description: Optional task description
        estimated_pomodoros: Optional estimated number of pomodoros

    Returns:
        Created task
    """
    task = Task(
        title=title,
        description=description,
        estimated_pomodoros=estimated_pomodoros
    )

    # Add to daily state
    state = load_daily_state()
    state.tasks.append(task)
    save_daily_state(state)

    return task


def get_task_by_id(task_id: str) -> Optional[Task]:
    """
    Get a task by ID

    Args:
        task_id: Task ID

    Returns:
        Task if found, None otherwise
    """
    state = load_daily_state()

    # Check current task
    if state.current_task and state.current_task.id == task_id:
        return state.current_task

    # Check task list
    for task in state.tasks:
        if task.id == task_id:
            return task

    return None


def list_tasks(status: Optional[TaskStatus] = None) -> List[Task]:
    """
    List tasks, optionally filtered by status

    Args:
        status: Optional status filter

    Returns:
        List of tasks
    """
    state = load_daily_state()
    tasks = state.tasks.copy()

    # Include current task if it exists
    if state.current_task:
        tasks.insert(0, state.current_task)

    if status:
        tasks = [t for t in tasks if t.status == status]

    return tasks


def update_task_progress(task_id: str, percentage: int) -> Optional[Task]:
    """
    Update task completion percentage

    Args:
        task_id: Task ID
        percentage: Completion percentage (0-100)

    Returns:
        Updated task if found, None otherwise
    """
    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100")

    state = load_daily_state()
    updated_task = None

    # Update current task
    if state.current_task and state.current_task.id == task_id:
        state.current_task.completion_percentage = percentage
        updated_task = state.current_task

    # Update in task list
    for i, task in enumerate(state.tasks):
        if task.id == task_id:
            state.tasks[i].completion_percentage = percentage
            updated_task = state.tasks[i]
            break

    if updated_task:
        save_daily_state(state)

    return updated_task


def mark_task_completed(task_id: str) -> Optional[Task]:
    """
    Mark a task as completed

    Args:
        task_id: Task ID

    Returns:
        Completed task if found, None otherwise
    """
    state = load_daily_state()
    completed_task = None

    # Check current task
    if state.current_task and state.current_task.id == task_id:
        state.current_task.status = TaskStatus.COMPLETED
        state.current_task.completion_percentage = 100
        state.current_task.completed_at = datetime.now()
        completed_task = state.current_task

        # Archive to completed tasks
        save_completed_tasks([state.current_task])

        # Clear current task
        state.current_task = None

    # Check task list
    else:
        for i, task in enumerate(state.tasks):
            if task.id == task_id:
                state.tasks[i].status = TaskStatus.COMPLETED
                state.tasks[i].completion_percentage = 100
                state.tasks[i].completed_at = datetime.now()
                completed_task = state.tasks[i]

                # Archive to completed tasks
                save_completed_tasks([state.tasks[i]])

                # Remove from task list
                state.tasks.pop(i)
                break

    if completed_task:
        save_daily_state(state)

    return completed_task


def set_current_task(task_id: str) -> Optional[Task]:
    """
    Set a task as the current task

    Args:
        task_id: Task ID

    Returns:
        Task if found, None otherwise
    """
    state = load_daily_state()

    # Find task in list
    for i, task in enumerate(state.tasks):
        if task.id == task_id:
            # Move current task back to list if exists
            if state.current_task:
                state.tasks.append(state.current_task)

            # Set new current task
            state.current_task = state.tasks.pop(i)
            state.current_task.status = TaskStatus.IN_PROGRESS

            if not state.current_task.started_at:
                state.current_task.started_at = datetime.now()

            save_daily_state(state)
            return state.current_task

    # Check if it's already the current task
    if state.current_task and state.current_task.id == task_id:
        return state.current_task

    return None


def get_current_task() -> Optional[Task]:
    """
    Get the current task

    Returns:
        Current task if exists, None otherwise
    """
    state = load_daily_state()
    return state.current_task


def delete_task(task_id: str) -> bool:
    """
    Delete a task

    Args:
        task_id: Task ID

    Returns:
        True if deleted, False otherwise
    """
    state = load_daily_state()

    # Check current task
    if state.current_task and state.current_task.id == task_id:
        state.current_task = None
        save_daily_state(state)
        return True

    # Check task list
    for i, task in enumerate(state.tasks):
        if task.id == task_id:
            state.tasks.pop(i)
            save_daily_state(state)
            return True

    return False


def increment_pomodoro_count(task_id: str) -> Optional[Task]:
    """
    Increment the pomodoro count for a task

    Args:
        task_id: Task ID

    Returns:
        Updated task if found, None otherwise
    """
    state = load_daily_state()
    updated_task = None

    # Update current task
    if state.current_task and state.current_task.id == task_id:
        state.current_task.pomodoros_completed += 1
        updated_task = state.current_task

    # Update in task list
    for i, task in enumerate(state.tasks):
        if task.id == task_id:
            state.tasks[i].pomodoros_completed += 1
            updated_task = state.tasks[i]
            break

    if updated_task:
        save_daily_state(state)

    return updated_task


def get_task_summary() -> dict:
    """
    Get summary statistics for tasks

    Returns:
        Dictionary with task statistics
    """
    tasks = list_tasks()

    total_tasks = len(tasks)
    todo_tasks = len([t for t in tasks if t.status == TaskStatus.TODO])
    in_progress_tasks = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
    completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])

    total_pomodoros = sum(t.pomodoros_completed for t in tasks)

    return {
        "total_tasks": total_tasks,
        "todo": todo_tasks,
        "in_progress": in_progress_tasks,
        "completed": completed_tasks,
        "total_pomodoros": total_pomodoros
    }
