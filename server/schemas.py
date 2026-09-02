from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_moderator: bool
    is_playtester: bool
    official_stars: int
    user_stars: int
    stars: int
    creator_points: int
    playtime_seconds: int
    demons_beaten: int
    icon_cube: int
    icon_ship: int
    icon_ball: int
    icon_wave: int
    icon_ufo: int
    color1: str
    color2: str
    created_at: int
    
    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseModel):
    icon_cube: Optional[int] = None
    icon_ship: Optional[int] = None
    icon_ball: Optional[int] = None
    icon_wave: Optional[int] = None
    icon_ufo: Optional[int] = None
    color1: Optional[str] = None
    color2: Optional[str] = None

class LevelUpload(BaseModel):
    title: str # Kept for backward compatibility, but conceptually lives on Level
    level_id: Optional[str] = None
    suggested_difficulty: Optional[int] = 0 # If provided, it's an update to an existing level
    data: str

class LevelVersionResponse(BaseModel):
    id: int
    version_number: int
    is_current_published: bool
    status: str
    stars: int
    plays: int
    created_at: int
    
    model_config = ConfigDict(from_attributes=True)

class LevelResponse(BaseModel):
    id: int
    level_id: str
    title: str
    creator_id: Optional[int] = None
    created_at: int
    creator_name: Optional[str] = None
    
    # Injected data from the currently published version
    published_version_id: Optional[int] = None
    stars: Optional[int] = None
    plays: Optional[int] = None
    community_rating: Optional[int] = None
    ratings_count: Optional[int] = None
    likes: int = 0
    dislikes: int = 0
    has_reacted: Optional[str] = None # "like", "dislike", or null
    has_rated: Optional[bool] = None
    requested_stars: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class LevelDataResponse(LevelResponse):
    data: str # The level data from the published version

class RatingCreate(BaseModel):
    rating: int

class CommentCreate(BaseModel):
    text: str

class CommentResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    level_id: int
    text: str
    created_at: int
    author_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
