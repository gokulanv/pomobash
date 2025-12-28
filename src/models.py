"""Data models for Pomobash timer application"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class TimerDuration(Enum):
    """Available timer durations in minutes"""
    SHORT = 24
    MEDIUM = 40
    LONG = 60


class BreakDuration(Enum):
    """Available break durations in minutes"""
    SHORT = 5
    MEDIUM = 10
    LONG = 20


class TaskStatus(Enum):
    """Task status states"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Task(BaseModel):
    """Represents a task to be worked on"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    completion_percentage: int = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pomodoros_completed: int = 0
    estimated_pomodoros: Optional[int] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            TaskStatus: lambda v: v.value,
        }


class PomodoroSession(BaseModel):
    """Represents a single Pomodoro session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None
    task_title: str
    duration_minutes: int
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    completed: bool = False
    interrupted: bool = False
    notes: Optional[str] = None
    is_break: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class DailyState(BaseModel):
    """Represents the current day's state"""
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    current_task: Optional[Task] = None
    tasks: List[Task] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            TaskStatus: lambda v: v.value,
        }


class CompletedTasksLog(BaseModel):
    """Log of completed tasks"""
    tasks: List[Task] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            TaskStatus: lambda v: v.value,
        }


class SessionsLog(BaseModel):
    """Log of all Pomodoro sessions"""
    sessions: List[PomodoroSession] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
