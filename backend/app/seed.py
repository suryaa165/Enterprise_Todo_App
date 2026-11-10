from sqlalchemy import select
from .database import SessionLocal, Base, engine
from .models import User, Task
from .security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    if not db.scalar(select(User).where(User.email == "admin@todo.com")):
        db.add(User(name="Administrator", email="admin@todo.com",
                    hashed_password=hash_password("Admin123!ChangeMe"), role="admin"))
    defaults = [
        ("Morning workout", "Complete your planned exercise session", "Fitness"),
        ("Walking", "Daily walk", "Fitness"),
        ("Study Python", "Practice Python programming", "Learning"),
        ("Study system design", "Learn one system design concept", "Learning"),
        ("Drink water", "Meet your daily hydration target", "Health"),
        ("Meditation", "Mindfulness session", "Health"),
        ("Sleep on time", "Follow your planned sleep schedule", "Personal"),
        ("Read a book", "Read for at least 20 minutes", "Personal"),
    ]
    for title, description, category in defaults:
        if not db.scalar(select(Task).where(Task.title == title)):
            db.add(Task(title=title, description=description, category=category))
    db.commit()
finally:
    db.close()
print("Seed complete. Admin: admin@todo.com / Admin123!ChangeMe")
