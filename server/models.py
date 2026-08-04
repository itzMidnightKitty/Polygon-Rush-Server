from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from .database import Base
import time

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    points = Column(Integer, default=0) # Unused? We'll keep it or ignore it
    is_admin = Column(Boolean, default=False)
    is_moderator = Column(Boolean, default=False)
    
    # Progression
    official_stars = Column(Integer, default=0)
    user_stars = Column(Integer, default=0)
    creator_points = Column(Integer, default=0)
    
    # Icons
    icon_cube = Column(Integer, default=0)
    icon_ship = Column(Integer, default=0)
    icon_ball = Column(Integer, default=0)
    icon_wave = Column(Integer, default=0)
    icon_ufo = Column(Integer, default=0)
    color1 = Column(String, default="255,255,255")
    color2 = Column(String, default="0,255,255")

    created_at = Column(Integer, default=lambda: int(time.time()))

    @property
    def stars(self):
        return (self.official_stars or 0) + (self.user_stars or 0)

    levels = relationship("Level", back_populates="creator")
    comments = relationship("Comment", back_populates="author")
    ratings = relationship("Rating", back_populates="user")
    completions = relationship("LevelCompletion", back_populates="user")

class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(String, unique=True, index=True) # e.g. "8-char-uuid"
    title = Column(String, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(Integer, default=lambda: int(time.time()))

    creator = relationship("User", back_populates="levels")
    versions = relationship("LevelVersion", back_populates="level", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="level")
    likes = relationship("LevelLike", back_populates="level", cascade="all, delete-orphan")

class LevelVersion(Base):
    __tablename__ = "level_versions"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"))
    version_number = Column(Integer, default=1)
    is_current_published = Column(Boolean, default=False)
    data = Column(Text)
    status = Column(String, default="pending") # pending, published, rejected, sent_to_admin
    stars = Column(Integer, default=0) # Assigned by admin
    requested_stars = Column(Integer, default=0) # Requested by the uploader
    moderator_suggested_stars = Column(Integer, default=0) # Suggested by a moderator when sending to admin
    sent_by_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Moderator who sent this to the admin
    created_at = Column(Integer, default=lambda: int(time.time()))

    # Stats specific to this version
    plays = Column(Integer, default=0)

    level = relationship("Level", back_populates="versions")
    ratings = relationship("Rating", back_populates="version")
    completions = relationship("LevelCompletion", back_populates="version")
    sent_by = relationship("User", foreign_keys=[sent_by_id])

class LevelCompletion(Base):
    __tablename__ = "level_completions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level_version_id = Column(Integer, ForeignKey("level_versions.id"))
    completed_at = Column(Integer, default=lambda: int(time.time()))

    user = relationship("User", back_populates="completions")
    version = relationship("LevelVersion", back_populates="completions")

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level_version_id = Column(Integer, ForeignKey("level_versions.id"))
    rating = Column(Integer) # 1-5 (Player rating)

    version = relationship("LevelVersion", back_populates="ratings")
    user = relationship("User", back_populates="ratings")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level_id = Column(Integer, ForeignKey("levels.id"))
    text = Column(Text)
    created_at = Column(Integer, default=lambda: int(time.time()))

    author = relationship("User", back_populates="comments")
    level = relationship("Level", back_populates="comments")

class LevelLike(Base):
    __tablename__ = "level_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level_id = Column(Integer, ForeignKey("levels.id"))
    is_like = Column(Boolean, default=True) # True for like, False for dislike
    created_at = Column(Integer, default=lambda: int(time.time()))

    level = relationship("Level", back_populates="likes")
    user = relationship("User")
