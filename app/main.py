from fastapi import FastAPI, Depends, HTTPException, status,Path, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from . import models, schemas, auth
from .auth import get_current_user, admin_required
from .database import Base, engine, SessionLocal, get_db



Base.metadata.create_all(bind = engine)

app = FastAPI()

@app.get("/")
def read_root():
  return {"message": "Task Manager API is running!"}

def send_email_notification(username: str, task_title:str):
   print(f"Email sent to {username}: Your task '{task_title}' was created successfully!")

# register
@app.post("/register", response_model = schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):

  existing_user = db.query(models.User).filter(models.User.email == user.email).first()
  if existing_user:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail= "Email already registered"
    )
  
  hashed_password = auth.hash_password(user.password)

  new_user = models.User(
    username = user.username,
    email = user.email,
    password = hashed_password
  )

  db.add(new_user)
  db.commit()
  db.refresh(new_user)

  return new_user

# login
@app.post("/login", response_model=schemas.Token)
def logon(form_data: OAuth2PasswordRequestForm= Depends(), db: Session = Depends(get_db)):

  user = db.query(models.User).filter(models.User.email == form_data.username).first()

  if not user or not auth.verify_password(form_data.password, user.password):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail= "Invalid credentials",
      headers= {"WWW-Authenticate" : " Bearer"}
    )
  
  access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
  access_token = auth.create_access_token(data= {"sub":str(user.id)}, expires_delta=access_token_expires)

  return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(current_user: models.User = Depends(get_current_user)):
  return {
    "id": current_user.id,
    "username": current_user.username,
    "email": current_user.email,
    "is_admin":current_user.is_admin
  }

@app.get("/admin/secret")
def read_admin_secret(current_user: models.User = Depends(admin_required)):
  return {"message": f"Welcome Admin {current_user.username}"}

@app.put("/users/{user_id}/promote", response_model=schemas.UserResponse)
def promote_user(
  user_id: int,
  db:Session = Depends(get_db),
  current_user: models.User = Depends(auth.get_current_user)
):
  if not current_user.is_admin:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="You are not allowed to promote users."
    )
  
  user = db.query(models.User).filter(models.User.id == user_id).first()

  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  user.is_admin = True
  db.commit()
  db.refresh(user)

  return user

@app.post("/tasks/", response_model=schemas.TaskResponse)
def create_task(
  task: schemas.TaskCreate,db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
  background_tasks: BackgroundTasks = None
):
   if not task.title.strip():  # check if title is empty or just spaces
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task title cannot be empty"
        )
  
   db_task = models.Task(
        title=task.title,
        description=task.description,
        completed=task.completed,
        owner_id=current_user.id,  # auto-assign task to logged-in user
    )
   db.add(db_task)
   db.commit()
   db.refresh(db_task)

   background_tasks.add_task(send_email_notification, current_user.username, task.title)
   
   return db_task

@app.get("/tasks/",response_model=list[schemas.TaskResponse])
def get_tasks(
  skip: int= 0,
  limit: int = 10,
  sort_by: str = "id",
  order: str = "asc",
  search: str = None,
  db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
  tasks_query = db.query(models.Task).filter(models.Task.owner_id == current_user.id)

  if search:
     tasks_query = tasks_query.filter(models.Task.title.ilike(f"%{search}%"))

  if sort_by in ["id","title", "completed"]:
     column_attr = getattr(models.Task, sort_by)
     tasks_query = tasks_query.order_by(column_attr.desc()  if order == "desc" else column_attr.asc())
    

  
  tasks = tasks_query.offset(skip).limit(limit).all()
  return tasks



@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task_by_id(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
  task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.owner_id == current_user.id).first()
  if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )

  return task


@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(
   task_id: int = Path(...,  description="ID of the task to update"),task_update: schemas.TaskUpdate = ..., db: Session = Depends(get_db),current_user: models.User = Depends(get_current_user)
):
   task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.owner_id == current_user.id
    ).first()
   if not task:
      raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
   if task.owner_id != current_user.id:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to update this task"
    )
   if task_update.title is not None:
      task.title = task_update.title.strip()
   if task_update.description is not None:
      task.description = task_update.description.strip()
   if task_update.completed is not None:
        task.completed = task_update.completed

   db.commit()
   db.refresh(task)
   return task


@app.delete("/tasks/{task_id}", response_model=schemas.TaskResponse)
def delete_task(
   task_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
   task = db.query(models.Task).filter(models.Task.id == task_id).first()

   if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
   if task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this task"
        )

   db.delete(task)
   db.commit()
    
   return task

@app.get("/admin/users", response_model=list[schemas.UserResponse])
def get_all_users(
  db: Session = Depends(get_db),
  current_user: models.User = Depends(auth.admin_required)
):
   users = db.query(models.User).all()
   return users
   
@app.delete("/admin/users/{user_id}", response_model=schemas.UserResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_required)  # Only admins
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return user