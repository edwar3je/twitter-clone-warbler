"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

with app.app_context():
    db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        with app.app_context():
            User.query.delete()
            Message.query.delete()
            Follows.query.delete()

            self.client = app.test_client()

            self.testuser = User.signup(username="testuser",
                                        email="test@test.com",
                                        password="testuser",
                                        image_url=User.image_url.default.arg)

            db.session.commit()

            testuser_extract1 = User.query.filter(User.username == "testuser").first()

            testuser2 = User(username="testuser2", email="some@test.com", password="password", image_url=User.image_url.default.arg)
            db.session.add(testuser2)
            db.session.commit()

            testuser_extract2 = User.query.filter(User.username == "testuser2").first()

            testuser3 = User(username="testuser3", email="bot@test.com", password="something", image_url=User.image_url.default.arg)
            db.session.add(testuser3)
            db.session.commit()

            testuser_extract3 = User.query.filter(User.username == "testuser3").first()
            
            message_1 = Message(text="First message.", timestamp=Message.timestamp.default.arg, user_id=testuser_extract1.id)
            message_2 = Message(text="Second message.", timestamp=Message.timestamp.default.arg, user_id=testuser_extract1.id)
            message_3 = Message(text="First other message.", timestamp=Message.timestamp.default.arg, user_id=testuser_extract2.id)
            message_4 = Message(text="Yet another message.", timestamp=Message.timestamp.default.arg, user_id=testuser_extract3.id)

            db.session.add(message_1)
            db.session.add(message_2)
            db.session.add(message_3)
            db.session.commit()

            follow_1 = Follows(user_being_followed_id=testuser_extract2.id, user_following_id=testuser_extract1.id)
            db.session.add(follow_1)
            db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        # You need to extract the new user's id before you can do this. To do this, you can't use
        # .signup because that creates a NEW instance. Instead, just extract the user by username
        # then extract the id and place it inside session[CURR_USER_KEY]. 
        with app.app_context():
            new_user = User.query.filter(User.username == "testuser").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = new_user.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            # Extract the most recent message added
            new_msg = Message.query.filter(Message.text == "Hello").first()
            self.assertEqual(new_msg.text, "Hello")
    
    def test_view_message(self):
        """Allows (logged-in) user to see message."""
        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            
            msg = Message.query.filter(Message.text == "First message.").first()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id

            resp = c.get(f"/messages/{msg.id}")
            html = resp.get_data(as_text=True)

            # Response should lead to a direct page (no redirects)
            self.assertEqual(resp.status_code, 200)

            # Response should display a message (in this case, the latest message from setUp()).
            self.assertIn("First message.", html)
    
    def test_delete_message(self):
        """Allows (logged-in) user to delete (their own) message."""
        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()

            msg = Message.query.filter(Message.text == "First message.").first()

            other_msg = Message.query.filter(Message.text == "First other message.").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id

            resp = c.post(f"/messages/{msg.id}/delete")

            # Response should redirect user.
            self.assertEqual(resp.status_code, 302)
            
            # Message should no longer appear once deleted.
            self.assertFalse(Message.query.filter(Message.text == "First message.").first())


        with self.client as d:
            with d.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id

            resp2 = d.post(f"/messages/{other_msg.id}/delete")

            # Attempting to delete another user's message should redirect the user 
            self.assertEqual(resp2.status_code, 302)

            # Attempting to delete another user's message should not work (message should still be there)
            self.assertTrue(Message.query.filter(Message.text == "First other message.").first())
    
    def test_display_all_messages(self):
        """If a user is logged in, displays all the messages of that user and the accounts
        they follow."""
        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp = c.get("/")
            html = resp.get_data(as_text=True)

            # The page should display if logged in (not redirect)
            self.assertEqual(resp.status_code, 200)

            # The user should be able to see their own messages
            self.assertIn("First message.", html)

            # The user should be able to see the messages of any account they follow
            self.assertIn("First other message.", html)

            # The user should not be able to see the messages of any account they don't follow
            self.assertNotIn("Yet another message.", html)