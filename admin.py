def delete_user(current_user, database, user_id):
    database.delete(user_id)
