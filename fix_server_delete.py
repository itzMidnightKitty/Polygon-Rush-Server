with open('server/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_del = '''@app.delete("/users/me")
def delete_my_account(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db.delete(current_user)
    db.commit()
    return {"success": True}'''

new_del = '''@app.delete("/users/me")
def delete_my_account(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Reassign or delete user's content to avoid ForeignKey constraint errors
    db.query(models.Level).filter(models.Level.creator_id == current_user.id).update({"creator_id": None})
    db.query(models.Comment).filter(models.Comment.user_id == current_user.id).delete()
    db.query(models.LevelLike).filter(models.LevelLike.user_id == current_user.id).delete()
    db.query(models.LevelCompletion).filter(models.LevelCompletion.user_id == current_user.id).delete()
    db.query(models.Rating).filter(models.Rating.user_id == current_user.id).delete()
    
    db.delete(current_user)
    db.commit()
    return {"success": True}'''

content = content.replace(old_del, new_del)

with open('server/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed server delete user')
