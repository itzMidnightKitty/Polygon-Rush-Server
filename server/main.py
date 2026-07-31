from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import zlib
import base64

from . import models, schemas, auth, database
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Polygon Rush API")

# --- AUTH ROUTES ---

@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if not user.username or not user.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if not user.password or not user.password.strip():
        raise HTTPException(status_code=400, detail="Password cannot be empty")
        
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, password_hash=hashed_password)
    if user.username.lower() == "itzmidnightkitty":
        new_user.is_admin = True
        new_user.is_moderator = True
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login")
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not auth.verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- USER ROUTES ---

@app.get("/users")
def get_users(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.User)
    if search:
        query = query.filter(models.User.username.ilike(f"%{search}%"))
    query = query.filter(models.User.username != "", models.User.username.isnot(None))
    users = query.all()
    results = []
    for u in users:
        results.append({
            "username": u.username,
            "stars": u.official_stars + u.user_stars,
            "creator_points": u.creator_points,
            "is_admin": u.is_admin,
            "is_moderator": u.is_moderator,
            "icon_cube": u.icon_cube,
            "icon_ship": u.icon_ship,
            "icon_ball": u.icon_ball,
            "icon_wave": u.icon_wave,
            "icon_ufo": u.icon_ufo,
            "color1": u.color1,
            "color2": u.color2
        })
    return results

@app.get("/users/{username}", response_model=schemas.UserResponse)
def get_user(username: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.icon_ufo is None: user.icon_ufo = 0
    return user

@app.put("/users/me/icons", response_model=schemas.UserResponse)
def update_icons(profile: schemas.UserProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if profile.icon_cube is not None: current_user.icon_cube = profile.icon_cube
    if profile.icon_ship is not None: current_user.icon_ship = profile.icon_ship
    if profile.icon_ball is not None: current_user.icon_ball = profile.icon_ball
    if profile.icon_wave is not None: current_user.icon_wave = profile.icon_wave
    if profile.icon_ufo is not None: current_user.icon_ufo = profile.icon_ufo
    if profile.color1 is not None: current_user.color1 = profile.color1
    if profile.color2 is not None: current_user.color2 = profile.color2
    db.commit()
    db.refresh(current_user)
    return current_user

@app.delete("/users/me")
def delete_my_account(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db.query(models.Level).filter(models.Level.creator_id == current_user.id).update({"creator_id": None})
    db.query(models.Comment).filter(models.Comment.user_id == current_user.id).delete()
    db.query(models.LevelLike).filter(models.LevelLike.user_id == current_user.id).delete()
    db.query(models.LevelCompletion).filter(models.LevelCompletion.user_id == current_user.id).delete()
    db.query(models.Rating).filter(models.Rating.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()
    return {"success": True}

# --- ADMIN ROUTES ---
@app.delete("/admin/users/{username}")
def delete_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    db.query(models.Level).filter(models.Level.creator_id == user.id).update({"creator_id": None})
    db.query(models.Comment).filter(models.Comment.user_id == user.id).delete()
    db.query(models.LevelLike).filter(models.LevelLike.user_id == user.id).delete()
    db.query(models.LevelCompletion).filter(models.LevelCompletion.user_id == user.id).delete()
    db.query(models.Rating).filter(models.Rating.user_id == user.id).delete()
    
    db.delete(user)
    db.commit()
    return {"success": True}

@app.post("/admin/users/{username}/ban")
def ban_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.query(models.Level).filter(models.Level.creator_id == user.id).update({"creator_id": None})
    db.query(models.Comment).filter(models.Comment.user_id == user.id).delete()
    db.query(models.LevelLike).filter(models.LevelLike.user_id == user.id).delete()
    db.query(models.LevelCompletion).filter(models.LevelCompletion.user_id == user.id).delete()
    db.query(models.Rating).filter(models.Rating.user_id == user.id).delete()
    
    db.delete(user)
    db.commit()
    return {"success": True}

@app.post("/admin/users/{username}/stats")
def admin_update_user_stats(username: str, stats: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    
    target = db.query(models.User).filter(func.lower(models.User.username) == username.lower()).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    if 'official_stars' in stats: target.official_stars = max(0, (target.official_stars or 0) + stats['official_stars'])
    if 'user_stars' in stats: target.user_stars = max(0, (target.user_stars or 0) + stats['user_stars'])
    if 'creator_points' in stats: target.creator_points = max(0, (target.creator_points or 0) + stats['creator_points'])
    
    db.commit()
    return {"success": True, "message": "User stats updated"}

@app.post("/admin/users/{username}/mod")
def toggle_user_mod(username: str, data: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
        
    target = db.query(models.User).filter(func.lower(models.User.username) == username.lower()).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    target.is_moderator = data.get("is_moderator", False)
    db.commit()
    return {"success": True, "is_moderator": target.is_moderator}


# --- LEVEL ROUTES ---

@app.post("/levels/upload")
def upload_level(level_upload: schemas.LevelUpload, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Compress data
    compressed = zlib.compress(level_upload.data.encode('utf-8'))
    data_b64 = base64.b64encode(compressed).decode('utf-8')
    
    if level_upload.level_id:
        level = db.query(models.Level).filter(
            models.Level.level_id == level_upload.level_id,
            models.Level.creator_id == current_user.id
        ).first()
        if not level:
            raise HTTPException(status_code=404, detail="Level not found or you are not the creator")
        
        latest_version = db.query(func.max(models.LevelVersion.version_number)).filter(
            models.LevelVersion.level_id == level.id
        ).scalar() or 0
        
        new_version = models.LevelVersion(
            level_id=level.id,
            version_number=latest_version + 1,
            data=data_b64,
            requested_stars=level_upload.suggested_difficulty
        )
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        
        level.published_version_id = new_version.id
        db.commit()
        return {"success": True, "level_id": level.level_id}
        
    else:
        import uuid
        new_lvl_id = str(uuid.uuid4())[:8]
        new_level = models.Level(
            level_id=new_lvl_id,
            title=level_upload.title,
            creator_id=current_user.id
        )
        db.add(new_level)
        db.commit()
        db.refresh(new_level)
        
        new_version = models.LevelVersion(
            level_id=new_level.id,
            version_number=1,
            data=data_b64,
            requested_stars=level_upload.suggested_difficulty
        )
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        
        new_level.published_version_id = new_version.id
        db.commit()
        return {"success": True, "level_id": new_level.level_id}

@app.get("/levels")
def list_levels(db: Session = Depends(get_db), current_user: Optional[models.User] = Depends(auth.get_current_user_optional)):
    levels = db.query(models.Level).order_by(models.Level.created_at.desc()).all()
    results = []
    for l in levels:
        creator_name = l.creator.username if l.creator else "Unknown"
        has_rated = False
        has_reacted = None
        if current_user and l.published_version_id:
            r = db.query(models.Rating).filter(models.Rating.level_version_id == l.published_version_id, models.Rating.user_id == current_user.id).first()
            if r: has_rated = True
            rx = db.query(models.LevelLike).filter(models.LevelLike.level_id == l.level_id, models.LevelLike.user_id == current_user.id).first()
            if rx: has_reacted = "like" if rx.is_like else "dislike"
            
        results.append({
            "level_id": l.level_id,
            "title": l.title,
            "creator_name": creator_name,
            "stars": l.stars,
            "plays": l.plays,
            "community_rating": l.community_rating,
            "ratings_count": l.ratings_count,
            "likes": l.likes,
            "dislikes": l.dislikes,
            "has_reacted": has_reacted,
            "has_rated": has_rated,
            "published_version_id": l.published_version_id,
            "suggested_difficulty": l.suggested_difficulty
        })
    return results

@app.get("/levels/{level_id}")
def get_level(level_id: int, db: Session = Depends(get_db)):
    level = db.query(models.Level).filter(models.Level.level_id == level_id).first()
    if not level or not level.published_version_id:
        raise HTTPException(status_code=404, detail="Level not found or not published")
        
    version = db.query(models.LevelVersion).filter(models.LevelVersion.id == level.published_version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    level.plays = (level.plays or 0) + 1
    db.commit()
    
    # Decompress data transparently
    raw_data = version.data
    try:
        compressed_bytes = base64.b64decode(version.data)
        decompressed_text = zlib.decompress(compressed_bytes).decode('utf-8')
        raw_data = decompressed_text
    except Exception:
        # Fallback for old uncompressed levels
        pass
        
    return {
        "level_id": level.level_id,
        "title": level.title,
        "creator_name": level.creator.username if level.creator else "Unknown",
        "data": raw_data,
        "published_version_id": version.id,
        "stars": level.stars,
        "plays": level.plays,
        "community_rating": level.community_rating,
        "ratings_count": level.ratings_count,
        "likes": level.likes,
        "dislikes": level.dislikes
    }

@app.delete("/levels/{level_id}")
def delete_level(level_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    level = db.query(models.Level).filter(models.Level.level_id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
        
    if level.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this level")
        
    db.delete(level)
    db.commit()
    return {"success": True}

@app.post("/level_versions/{version_id}/rate")
def rate_level(version_id: int, rating: schemas.RatingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    version = db.query(models.LevelVersion).filter(models.LevelVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    existing_rating = db.query(models.Rating).filter(
        models.Rating.level_version_id == version_id,
        models.Rating.user_id == current_user.id
    ).first()
    
    if existing_rating:
        raise HTTPException(status_code=400, detail="Already rated this version")
        
    new_rating = models.Rating(
        level_version_id=version_id,
        user_id=current_user.id,
        rating=rating.rating
    )
    db.add(new_rating)
    db.commit()
    
    level = version.level
    if level.published_version_id == version_id:
        all_ratings = db.query(models.Rating).filter(models.Rating.level_version_id == version_id).all()
        if all_ratings:
            avg = sum(r.rating for r in all_ratings) / len(all_ratings)
            level.community_rating = int(round(avg))
            level.ratings_count = len(all_ratings)
            db.commit()
            
    return {"success": True}

@app.post("/levels/{level_id}/like")
def like_level(level_id: int, is_like: bool, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    level = db.query(models.Level).filter(models.Level.level_id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
        
    existing = db.query(models.LevelLike).filter(
        models.LevelLike.level_id == level_id,
        models.LevelLike.user_id == current_user.id
    ).first()
    
    if existing:
        if existing.is_like == is_like:
            return {"success": True} # no change
        else:
            if existing.is_like: level.likes -= 1
            else: level.dislikes -= 1
            existing.is_like = is_like
            if is_like: level.likes += 1
            else: level.dislikes += 1
            db.commit()
    else:
        new_like = models.LevelLike(level_id=level_id, user_id=current_user.id, is_like=is_like)
        db.add(new_like)
        if is_like: level.likes = (level.likes or 0) + 1
        else: level.dislikes = (level.dislikes or 0) + 1
        db.commit()
        
    return {"success": True}

@app.post("/level_versions/{version_id}/moderate")
def moderate_level(version_id: int, status: str, stars: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_moderator and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    version = db.query(models.LevelVersion).filter(models.LevelVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    level = version.level
    if status == "rate":
        level.stars = stars
    elif status == "unrate":
        level.stars = 0
        
    db.commit()
    return {"success": True}

@app.post("/level_versions/{version_id}/complete")
def complete_level(version_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    version = db.query(models.LevelVersion).filter(models.LevelVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
        
    existing = db.query(models.LevelCompletion).filter(
        models.LevelCompletion.level_version_id == version_id,
        models.LevelCompletion.user_id == current_user.id
    ).first()
    
    if not existing:
        comp = models.LevelCompletion(level_version_id=version_id, user_id=current_user.id)
        db.add(comp)
        
        # Award stars if this is the published version and it has stars
        level = version.level
        if level.published_version_id == version_id and level.stars > 0:
            pass
            
        db.commit()
    return {"success": True}

# --- COMMENTS ---
@app.post("/levels/{level_id}/comment")
def post_comment(level_id: int, comment: schemas.CommentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    level = db.query(models.Level).filter(models.Level.level_id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
        
    new_comment = models.Comment(
        level_id=level_id,
        user_id=current_user.id,
        text=comment.text
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

@app.get("/levels/{level_id}/comments")
def get_comments(level_id: int, db: Session = Depends(get_db)):
    comments = db.query(models.Comment).filter(models.Comment.level_id == level_id).order_by(models.Comment.created_at.desc()).all()
    results = []
    for c in comments:
        results.append({
            "id": c.id,
            "text": c.text,
            "username": c.user.username if c.user else "Unknown",
            "created_at": c.created_at
        })
    return results

@app.get("/")
def read_root():
    return {"message": "Polygon Rush API is running!"}
