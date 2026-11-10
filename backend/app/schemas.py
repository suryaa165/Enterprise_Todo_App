from datetime import date, datetime
from pydantic import BaseModel, EmailStr, ConfigDict

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str

class TaskIn(BaseModel):
    title: str
    description: str = ""
    category: str = "General"

class TaskOut(TaskIn):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class RoutineIn(BaseModel):
    task_id: int
    target_value: str = ""

class RoutineOut(BaseModel):
    id: int
    task_id: int
    target_value: str
    is_active: bool
    task: TaskOut
    model_config = ConfigDict(from_attributes=True)

class CompletionIn(BaseModel):
    is_completed: bool

class DailyEntryOut(BaseModel):
    id: int
    routine_id: int
    task_date: date
    is_completed: bool
    completed_at: datetime | None
    title: str
    category: str

class DaySummary(BaseModel):
    date: date
    total: int
    completed: int
    percentage: float
