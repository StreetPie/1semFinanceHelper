from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

import logging

from database import get_db, SessionLocal, TransactionDB, BudgetDB, UserDB
import models  
from auth import ( #///
    authenticate_user, create_access_token, get_current_user,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Finance Assistant API",
    description="API для управления личными финансами",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"], #///
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    logger.info("Запуск Finance Assistant API...")
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Подключение к базе данных успешно")
    except Exception as e:
        logger.error(f" Ошибка подключения к базе данных: {e}")


@app.get("/")
def read_root():
    return {
        "message": "Finance Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")
        db_status = "disconnected"

    return {"status": "healthy", "database": db_status, "timestamp": datetime.now()}


@app.post("/register/", response_model=models.User)
def register(user: models.UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    logger.info(f"Регистрация пользователя: {user.username}")

    existing_user = db.query(UserDB).filter(
        UserDB.username == user.username
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    db_user = UserDB(
        username=user.username,
        password_hash=get_password_hash(user.password),
        role="user",
        settings={}
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"Пользователь зарегистрирован: ID={db_user.id}")
    return db_user


@app.post("/login/")
def login(form_data: models.UserCreate, db: Session = Depends(get_db)):
    """Вход в систему"""
    logger.info(f"Попытка входа: {form_data.username}")

    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Неудачная попытка входа: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    logger.info(f"Успешный вход: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me/", response_model=models.User)
def read_users_me(current_user: UserDB = Depends(get_current_user)):
    return current_user


@app.post("/transactions/", response_model=models.Transaction)
def create_transaction_auth(
        transaction: models.TransactionCreate,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(f"Создание транзакции пользователем {current_user.username}: {transaction}")

    db_transaction = TransactionDB(
        user_id=current_user.id,
        amount=transaction.amount,
        type=transaction.type,
        category=transaction.category,
        description=transaction.description,
        date=transaction.date,
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    logger.info(f"Транзакция создана с ID: {db_transaction.id}")
    return db_transaction


@app.get("/transactions/", response_model=List[models.Transaction])
def get_transactions_auth(
        skip: int = 0,
        limit: int = 100,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(f"Получение транзакций пользователя {current_user.username}")

    transactions = (
        db.query(TransactionDB)
        .filter(TransactionDB.user_id == current_user.id)
        .order_by(TransactionDB.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    logger.info(f"Найдено {len(transactions)} транзакций")
    return transactions


@app.post("/budgets/", response_model=models.Budget)
def create_budget_auth(
        budget: models.BudgetCreate,
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(f"Создание бюджета пользователем {current_user.username}: {budget}")

    db_budget = BudgetDB(
        user_id=current_user.id,
        category=budget.category,
        limit_amount=budget.limit_amount,
        period=budget.period,
    )

    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)

    logger.info(f"Бюджет создан с ID: {db_budget.id}")
    return db_budget


@app.get("/budgets/", response_model=List[models.Budget])
def get_budgets_auth(
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(f"Получение бюджетов пользователя {current_user.username}")

    budgets = db.query(BudgetDB).filter(BudgetDB.user_id == current_user.id).all()
    transactions = db.query(TransactionDB).filter(TransactionDB.user_id == current_user.id).all()

    for b in budgets:
        b.current_spent = sum(
            t.amount for t in transactions
            if t.category == b.category and t.type == "expense"
        )

    logger.info(f"Найдено {len(budgets)} бюджетов")
    return budgets


@app.get("/stats/")
def get_financial_stats_auth(
        current_user: UserDB = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(f"Расчет финансовой статистики пользователя {current_user.username}")

    transactions = db.query(TransactionDB).filter(TransactionDB.user_id == current_user.id).all()

    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expenses = sum(t.amount for t in transactions if t.type == "expense")
    balance = total_income - total_expenses

    expenses_by_category = {}
    for t in transactions:
        if t.type == "expense":
            expenses_by_category[t.category] = (
                    expenses_by_category.get(t.category, 0) + t.amount
            )

    stats = {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance,
        "expenses_by_category": expenses_by_category,
    }

    logger.info(f"Статистика: {stats}")
    return stats


@app.post("/transactions-test/", response_model=models.Transaction)
def create_transaction_test(
        transaction: models.TransactionCreate,
        db: Session = Depends(get_db)
):
    logger.info(f"Создание тестовой транзакции: {transaction}")

    user = db.query(UserDB).filter(UserDB.id == transaction.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    db_transaction = TransactionDB(
        user_id=transaction.user_id,
        amount=transaction.amount,
        type=transaction.type,
        category=transaction.category,
        description=transaction.description,
        date=transaction.date,
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    logger.info(f"Транзакция создана с ID: {db_transaction.id}")
    return db_transaction


@app.get("/transactions-test/", response_model=List[models.Transaction])
def get_transactions_test(
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    logger.info(f"Получение транзакций пользователя ID={user_id}")

    transactions = (
        db.query(TransactionDB)
        .filter(TransactionDB.user_id == user_id)
        .order_by(TransactionDB.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    logger.info(f"Найдено {len(transactions)} транзакций")
    return transactions


@app.get("/users/", response_model=List[models.User])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(UserDB).offset(skip).limit(limit).all()
    return users


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)