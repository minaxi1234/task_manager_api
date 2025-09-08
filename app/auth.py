from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .database import get_db  
from . import models, auth  
from jose import jwt, JWTError

# secret ket
SECRET_KEY ="your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")

def get_current_user(token:str = Depends(oauth2_scheme), db: Session= Depends(get_db)):
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
  )
  try:
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    user_id: str=payload.get("sub")
    if user_id is None:
      raise credentials_exception
  except JWTError:
    raise credentials_exception
  
  user = db.query(models.User).filter(models.User.id == int(user_id)).first()
  if user is None:
        raise credentials_exception

  return user



def create_access_token(data:dict, expires_delta: timedelta = None):
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.utcnow() + expires_delta
  else:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  to_encode.update({"exp": expire})
  encode_jwt = jwt.encode(to_encode, SECRET_KEY,algorithm=ALGORITHM)
  return encode_jwt

pwd_context = CryptContext(schemes= ["bcrypt"], deprecated= "auto")

def hash_password(password:str)-> str:
  return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
  return pwd_context.verify(plain_password, hashed_password)


def admin_required(current_user: models.User = Depends(get_current_user)):
  if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
  if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins only!",
        )
  return current_user