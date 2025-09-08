from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

ORM_CONFIG = {"from_attributes": True}

# -------- User schemas --------
class UserCreate(BaseModel):
  username: str
  email: EmailStr
  password: str

# Schema for showing user info (response model)
class UserResponse(BaseModel):
  id: int
  username: str
  email: EmailStr
  is_admin: bool

  model_config = ConfigDict(**ORM_CONFIG)

class Token(BaseModel):
  access_token: str
  token_type: str

  #  -------- Task schemas --------
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: Optional[bool] = False

    model_config = ConfigDict(**ORM_CONFIG)


class TaskUpdate(BaseModel):
    # All fields optional for partial updates
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

    model_config = ConfigDict(**ORM_CONFIG)


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool
    owner_id: int

    model_config = ConfigDict(**ORM_CONFIG)