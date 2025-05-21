# app/models/user.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.db_config import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(String, primary_key=True)
    email = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    address = Column(String)
    city = Column(String)
    gender = Column(String)
    photo_url = Column(String)
    country = Column(String(255))
    state = Column(String(255))
    zip_code = Column(String)
    status = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    deleted_at = Column(DateTime)
    deleted_by = Column(DateTime)

    permissions = relationship("UserPermissionRoles", backref="user", lazy=True)
    credit = relationship("Credit", back_populates="user", uselist=False)
    credit_usage = relationship("CreditUsage", back_populates="user")
    credit_history = relationship("CreditHistory", back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    users = relationship("UserPermissionRoles", backref="role", lazy=True)


class UserPermissionRoles(Base):
    __tablename__ = "user_permission_roles"

    user_id = Column(String, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime)
