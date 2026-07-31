with open('server/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_admin_del = '''@app.delete("/admin/users/{username}")
def delete_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()'''

new_admin_del = '''@app.delete("/admin/users/{username}")
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
    db.commit()'''

content = content.replace(old_admin_del, new_admin_del)

old_ban = '''@app.post("/admin/users/{username}/ban")
def ban_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # For now, deleting is equivalent to a permanent ban.
    db.delete(user)
    db.commit()'''

new_ban = '''@app.post("/admin/users/{username}/ban")
def ban_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # For now, deleting is equivalent to a permanent ban.
    db.query(models.Level).filter(models.Level.creator_id == user.id).update({"creator_id": None})
    db.query(models.Comment).filter(models.Comment.user_id == user.id).delete()
    db.query(models.LevelLike).filter(models.LevelLike.user_id == user.id).delete()
    db.query(models.LevelCompletion).filter(models.LevelCompletion.user_id == user.id).delete()
    db.query(models.Rating).filter(models.Rating.user_id == user.id).delete()
    
    db.delete(user)
    db.commit()'''

content = content.replace(old_ban, new_ban)

with open('server/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed server admin delete and ban')
