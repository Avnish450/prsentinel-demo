def delete_user(current_user, database, user_id):
    # SECURITY FIX: enforce admin permission (CVE-DEMO-0004)
    if not current_user.is_admin:
        raise PermissionError("Admin access required")
    database.delete(user_id)
