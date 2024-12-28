from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status


Base = declarative_base()


# Models
class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, autoincrement=True)
	username = Column(String, unique=True, nullable=False)
	hashed_password = Column(String, nullable=False)
	email = Column(String, unique=True, nullable=False)

	def __repr__(self):
		return f"User(id={self.id}, username={self.username}, email={self.email})"


class DBHelper:
	DATABASE_URL = "postgresql://ree:fWC9JkeNvMtFA26nmXX04TaBoTQzQHr2@dpg-ctnb3htumphs73c4qbeg-a.singapore-postgres.render.com/trekathon"

	def __init__(self):
		self.engine = create_engine(self.DATABASE_URL)
		self.test_connection()
		Session = sessionmaker(bind=self.engine)
		self.session = Session()

	def test_connection(self):
		try:
			with self.engine.connect() as conn:
				print("Connected to Database Successfully")
		except Exception as e:
			print("Error connecting to Database:", e)

	def fetch_all_users(self):
		users = self.session.query(User).all()
		return users

	def fetch_user_by_username(self, entered_username: str):
		user = self.session.query(User).filter(User.username == entered_username).first()
		if user is None:
			print("User not found")
		return user

	def register_user(self, user_dict: dict):
		try:
			new_user = User(**user_dict)  # Create the user object
			self.session.add(new_user)
			self.session.commit()
			self.session.refresh(new_user)  # Refresh to get latest data (e.g., auto-generated ID)
			print("User registered successfully", new_user)
			return new_user

		# Handle exceptions
		except IntegrityError as e:
			self.session.rollback()
			if 'users_email_key' in str(e.orig):  # Check if the error is related to the unique constraint on email
				raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Email is already registered")
			elif 'users_username_key' in str(e.orig):  # Check if the error is related to the unique constraint on username
				raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Username is already taken")
			else:
				# General error message for any other issues
				raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Failed to create User. Error: {e}")

		# For handling any other exceptions
		except Exception as e:
			self.session.rollback()
			print(e)
			raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Failed to create User. Error: {e}")

