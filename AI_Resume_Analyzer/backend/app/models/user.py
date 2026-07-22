from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)

    pdfs = relationship("UploadedPDF", back_populates="user", cascade="all, delete-orphan")

class UploadedPDF(Base):
    __tablename__ = "uploaded_pdfs"

    id = Column(Integer, primary_key=True, index=True)
    userId = Column(String, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    pages = Column(Integer, nullable=False)
    filepath = Column(String, nullable=False)

    user = relationship("User", back_populates="pdfs")
