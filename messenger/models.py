from messenger import db
import datetime

# I am sure i shouldn't create one more table in order to distinguish email and password from ordinary data. That will be hard and unnecessary
class User(db.Model):
    # Using autoincrement because faster and takes less memory
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(34), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(40), nullable=False)
    avatar = db.Column(db.String(12), nullable=False)
    bio = db.Column(db.String(70), nullable=False) # Excluding undefined 
    last_seen = db.Column(db.String(19), nullable=False)
    hashed_password = db.relationship('Password', backref="user", cascade='all,delete', lazy=True)
    
    __table_args__ = (
        db.Index('ix_email', 'email'),
    )

    def get_id(self):
        return (self.user_id)

    
class Password(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey(User.user_id, ondelete="CASCADE"), primary_key=True)
    hashed_password = db.Column(db.String(55), nullable=False)
    # Salt is binary format string.
    salt = db.Column(db.String(15), nullable=False)


class BlockedUsers(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    friend_id = db.Column(db.Integer, primary_key=True)

    __table_args__ = (
        db.Index('ix_blocked_pair', 'user_id', 'friend_id'),
    )

    # I want to reference that from user, not from blocked pair.
    # Note: we don't have self
    @staticmethod
    def are_blocked(user_id, friend_id):
        # This is done two times because one user blocks and another doesn't or they both. We should distinguish these situations
        return BlockedUsers.query.filter_by(user_id=user_id, friend_id=friend_id).first() is not None or \
            BlockedUsers.query.filter_by(user_id=friend_id, friend_id=user_id).first() is not None


    


