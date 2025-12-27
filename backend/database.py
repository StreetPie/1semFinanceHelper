from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)

Base = declarative_base()


class RoleDB(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)



class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    settings = Column(JSON, default={})

    incomes = relationship("IncomeDB", back_populates="user")
    savings = relationship("SavingsDB", back_populates="user")
    transactions = relationship("TransactionDB", back_populates="user")
    budgets = relationship("BudgetDB", back_populates="user")


class BudgetDB(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(100), nullable=False)
    limit_amount = Column(Float, nullable=False)
    period = Column(String(50), default="monthly")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("UserDB", back_populates="budgets")


class IncomeDB(Base):
    __tablename__ = "incomes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    source = Column(String(100), nullable=False)
    date = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)

    user = relationship("UserDB", back_populates="incomes")


class SavingsDB(Base):
    __tablename__ = "savings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total = Column(Float, default=0)
    goal = Column(String(500), nullable=True)

    user = relationship("UserDB", back_populates="savings")


class TransactionDB(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Float, nullable=False)
    type = Column(String(50), nullable=False)

    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserDB", back_populates="transactions")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы...")