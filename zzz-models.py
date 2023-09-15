from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Item(Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    posts = relationship("Post", backref="user")

class Post(Base):
    __tablename__ = "post"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(50))
    user_id = Column(Integer, ForeignKey("user.id"))
    