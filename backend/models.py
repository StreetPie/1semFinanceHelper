from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict


class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма транзакции")
    type: str = Field(..., pattern="^(income|expense)$", description="Тип: income или expense")
    category: str = Field(..., max_length=100, description="Категория")
    description: Optional[str] = Field(None, description="Описание")
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")


class TransactionCreate(TransactionBase):
    user_id: int = Field(1, description="ID пользователя")


class Transaction(TransactionBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BudgetBase(BaseModel):
    category: str = Field(..., max_length=100, description="Категория бюджета")
    limit_amount: float = Field(..., gt=0, description="Лимит бюджета")
    period: str = Field("monthly", description="Период: monthly, weekly, yearly")


class BudgetCreate(BudgetBase):
    user_id: int = Field(1, description="ID пользователя")


class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    current_spent: Optional[float] = 0  # Будет вычисляться

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    username: str = Field(..., max_length=100, description="Имя пользователя")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Пароль")


class User(UserBase):
    id: int
    role: str = "user"
    settings: Dict = {}

    class Config:
        from_attributes = True


class FinancialStats(BaseModel):
    total_income: float
    total_expenses: float
    balance: float
    expenses_by_category: Dict[str, float]


class Message(BaseModel):
    message: str


class HealthCheck(BaseModel):
    status: str
    database: str
    timestamp: datetime

    class Token(BaseModel):
        access_token: str
        token_type: str

    class TokenData(BaseModel):
        username: Optional[str] = None

    class UserBase(BaseModel):
        username: str = Field(..., max_length=100, description="Имя пользователя")

    class UserCreate(UserBase):
        password: str = Field(..., min_length=6, description="Пароль")

    class User(UserBase):
        id: int
        role: str = "user"
        settings: Dict = {}
        created_at: Optional[datetime] = None

        class Config:
            from_attributes = True