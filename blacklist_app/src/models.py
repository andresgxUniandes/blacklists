from src.database import db


class Blacklist(db.Model):
    __tablename__ = "blacklist"

    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, index=True, nullable=False)
    app_uuid = db.Column(db.String, nullable=False, index=True)
    blocked_reason = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
