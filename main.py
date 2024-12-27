from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel

from database import DBHelper, User

app = FastAPI()
DB = DBHelper()


@app.get("/")
async def home():
	return "HELLO"


@app.get("/get_all_users")
async def get_all_users():
	return DB.fetch_all_users()


@app.get("/get_user_by_username")
async def get_user_by_username(name: str):
	return DB.fetch_user_by_username(name)

# JWT settings
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
	access_token: str
	token_type: str


class TokenData(BaseModel):
	username: str | None = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def verify_password(plain_password, hashed_password):
	return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
	return pwd_context.hash(password)


def get_user(username: str):
	user = DB.fetch_user_by_username(username)
	return user


def authenticate_user(username: str, password: str):
	user = get_user(username)
	if not user:
		return False
	if not verify_password(password, user.hashed_password):
		return False
	return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.now(timezone.utc) + expires_delta
	else:
		expire = datetime.now(timezone.utc) + timedelta(minutes=15)
	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
	return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
		username: str = payload.get("sub")
		if username is None:
			raise credentials_exception
		token_data = TokenData(username=username)
	except InvalidTokenError:
		raise credentials_exception
	user = get_user(username=token_data.username)
	if user is None:
		raise credentials_exception
	return user


@app.post("/login")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
	user = authenticate_user(form_data.username, form_data.password)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Incorrect username or password",
			headers={"WWW-Authenticate": "Bearer"},
		)
	access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
	access_token = create_access_token(
		data={"sub": user.username}, expires_delta=access_token_expires
	)
	return {
		"status": "Login Successful",
		"user": user,
		"token": Token(access_token=access_token, token_type="bearer")
	}


@app.post("/register")
async def register(
		form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
		email: Annotated[str, Form()],
):
	user_dict = {
		"username": form_data.username,
		"email": email,
		"hashed_password": get_password_hash(form_data.password)
	}

	# UPDATE DATABASE
	new_user_from_db = DB.register_user(user_dict)  # Changed this to directly return the user model

	# RETURN TOKEN
	access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
	access_token = create_access_token(
		data={"sub": user_dict["username"]}, expires_delta=access_token_expires
	)
	return {
		"status": "User Created Successfully",
		"new_user": new_user_from_db,  # FastAPI will automatically handle the conversion to UserOut
		"token": Token(access_token=access_token, token_type="bearer")
	}


@app.get("/users/me/")
async def get_me(
		current_user: Annotated[User, Depends(get_current_user)],
):
	return current_user
