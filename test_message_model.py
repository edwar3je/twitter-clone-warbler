import os
from unittest import TestCase

from models import db, User, Message, Follows

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

from app import app

with app.app_context():
    db.create_all()

class MessageModelTestCase(TestCase):
    """Test if the message model works as expected."""

    def setUp(self):
        with app.app_context():
            User.query.delete()
            Message.query.delete()
            Follows.query.delete()

            self.client = app.test_client()

            db.session.commit()

    def test_message_model(self):
        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        with app.app_context():
            db.session.add(u)
            db.session.commit()
            new_u = User.query.filter(User.email == "test@test.com").first()
        
        m = Message(
            text="This is a test message.",
            user_id=new_u.id
        )

        with app.app_context():
            db.session.add(m)
            db.session.commit()
            new_m = Message.query.filter(Message.user_id == new_u.id).first()
            new_u = User.query.filter(User.email == "test@test.com").first()

            # See if the text of the message is equal to the instance
            self.assertEqual(new_m.text, "This is a test message.")
            # See if the user has at least 1 message
            self.assertEqual(len(new_u.messages), 1)