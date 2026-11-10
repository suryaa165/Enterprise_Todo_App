from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from .database import Base, engine, get_db
from .models import User, Task, UserRoutine, DailyTaskEntry
from .schemas import RegisterIn, LoginIn, TokenOut, TaskIn, TaskOut, RoutineIn, RoutineOut, CompletionIn, DailyEntryOut, DaySummary
from .security import hash_password, verify_password, create_token, current_user, admin_user
from .config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Todo Application API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.CORS_ORIGINS.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/auth/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "Email already registered")
    user = User(name=data.name, email=data.email, hashed_password=hash_password(data.password), role="customer")
    db.add(user); db.commit()
    return {"message": "Customer account created"}

@app.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    return TokenOut(access_token=create_token(user), role=user.role, name=user.name)

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}

@app.post("/api/admin/tasks", response_model=TaskOut, status_code=201)
def create_task(data: TaskIn, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    task = Task(**data.model_dump())
    db.add(task); db.commit(); db.refresh(task)
    return task

@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(category: str | None = None, q: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Task).where(Task.is_active == True)
    if category: stmt = stmt.where(Task.category == category)
    if q: stmt = stmt.where(Task.title.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(Task.category, Task.title)).all()

@app.patch("/api/admin/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, data: TaskIn, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    for key, value in data.model_dump().items(): setattr(task, key, value)
    db.commit(); db.refresh(task)
    return task

@app.delete("/api/admin/tasks/{task_id}")
def deactivate_task(task_id: int, db: Session = Depends(get_db), _: User = Depends(admin_user)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    task.is_active = False; db.commit()
    return {"message": "Task deactivated"}

@app.post("/api/routines", response_model=RoutineOut, status_code=201)
def add_routine(data: RoutineIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    task = db.get(Task, data.task_id)
    if not task or not task.is_active: raise HTTPException(404, "Active task not found")
    existing = db.scalar(select(UserRoutine).where(UserRoutine.user_id == user.id, UserRoutine.task_id == task.id))
    if existing:
        existing.is_active = True; existing.target_value = data.target_value
        routine = existing
    else:
        routine = UserRoutine(user_id=user.id, task_id=task.id, target_value=data.target_value)
        db.add(routine)
    db.commit()
    # Create today's entry immediately; future dates are generated when requested.
    ensure_day_entries(db, user.id, date.today())
    db.refresh(routine)
    return routine

@app.get("/api/routines", response_model=list[RoutineOut])
def my_routines(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.scalars(select(UserRoutine).options(joinedload(UserRoutine.task)).where(
        UserRoutine.user_id == user.id, UserRoutine.is_active == True).order_by(UserRoutine.id)).all()

@app.patch("/api/routines/{routine_id}")
def edit_routine(routine_id: int, data: RoutineIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    routine = db.get(UserRoutine, routine_id)
    if not routine or routine.user_id != user.id: raise HTTPException(404, "Routine not found")
    task = db.get(Task, data.task_id)
    if not task: raise HTTPException(404, "Task not found")
    routine.task_id = data.task_id; routine.target_value = data.target_value
    db.commit()
    return {"message": "Routine updated"}

@app.delete("/api/routines/{routine_id}")
def remove_routine(routine_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    routine = db.get(UserRoutine, routine_id)
    if not routine or routine.user_id != user.id: raise HTTPException(404, "Routine not found")
    routine.is_active = False; db.commit()
    return {"message": "Routine removed"}

def ensure_day_entries(db: Session, user_id: int, day: date):
    routines = db.scalars(select(UserRoutine).where(UserRoutine.user_id == user_id, UserRoutine.is_active == True)).all()
    for routine in routines:
        exists = db.scalar(select(DailyTaskEntry).where(DailyTaskEntry.routine_id == routine.id, DailyTaskEntry.task_date == day))
        if not exists:
            db.add(DailyTaskEntry(user_id=user_id, routine_id=routine.id, task_date=day, is_completed=False))
    db.commit()

@app.get("/api/daily", response_model=list[DailyEntryOut])
def daily_tasks(day: date = Query(default_factory=date.today), db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_day_entries(db, user.id, day)
    rows = db.scalars(select(DailyTaskEntry).options(joinedload(DailyTaskEntry.routine).joinedload(UserRoutine.task))
        .where(DailyTaskEntry.user_id == user.id, DailyTaskEntry.task_date == day)).all()
    return [DailyEntryOut(id=r.id, routine_id=r.routine_id, task_date=r.task_date, is_completed=r.is_completed,
                          completed_at=r.completed_at, title=r.routine.task.title, category=r.routine.task.category) for r in rows
            if r.routine.is_active]

@app.patch("/api/daily/{entry_id}")
def complete_task(entry_id: int, data: CompletionIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    entry = db.get(DailyTaskEntry, entry_id)
    if not entry or entry.user_id != user.id: raise HTTPException(404, "Daily entry not found")
    entry.is_completed = data.is_completed
    entry.completed_at = datetime.now(timezone.utc) if data.is_completed else None
    db.commit()
    return {"message": "Completion updated"}

@app.get("/api/history", response_model=list[DaySummary])
def history(days: int = Query(default=30, ge=1, le=30), db: Session = Depends(get_db), user: User = Depends(current_user)):
    today = date.today()
    result = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        ensure_day_entries(db, user.id, day)
        entries = db.scalars(select(DailyTaskEntry).join(UserRoutine).where(
            DailyTaskEntry.user_id == user.id, DailyTaskEntry.task_date == day, UserRoutine.is_active == True)).all()
        total = len(entries); completed = sum(1 for e in entries if e.is_completed)
        result.append(DaySummary(date=day, total=total, completed=completed,
                                 percentage=round(completed * 100 / total, 1) if total else 0))
    return result

@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db), _: User = Depends(admin_user)):
    users = db.scalars(select(User).where(User.role == "customer").order_by(User.id)).all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]

@app.get("/api/admin/users/{user_id}/history", response_model=list[DaySummary])
def user_history(user_id: int, days: int = Query(default=30, ge=1, le=30), db: Session = Depends(get_db), _: User = Depends(admin_user)):
    target = db.get(User, user_id)
    if not target: raise HTTPException(404, "User not found")
    today = date.today(); result = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset); ensure_day_entries(db, user_id, day)
        entries = db.scalars(select(DailyTaskEntry).join(UserRoutine).where(
            DailyTaskEntry.user_id == user_id, DailyTaskEntry.task_date == day, UserRoutine.is_active == True)).all()
        total = len(entries); completed = sum(1 for e in entries if e.is_completed)
        result.append(DaySummary(date=day, total=total, completed=completed,
                                 percentage=round(completed * 100 / total, 1) if total else 0))
    return result
