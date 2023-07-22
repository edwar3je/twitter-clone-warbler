"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

with app.app_context():
    db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        with app.app_context():
            User.query.delete()
            Message.query.delete()
            Follows.query.delete()

            self.client = app.test_client()

            db.session.commit()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        with app.app_context():
            db.session.add(u)
            db.session.commit()
            new_u = User.query.filter(User.email == "test@test.com").first()

            # User should have no messages & no followers
            self.assertEqual(len(new_u.messages), 0)
            self.assertEqual(len(new_u.followers), 0)

    def test_repr_model(self):
        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        with app.app_context():
            db.session.add(u)
            db.session.commit()
            new_u = User.query.filter(User.email == "test@test.com").first()

            # The repr method should create the following string for User instance new_u
            self.assertEqual(new_u.__repr__(), f"<User #{new_u.id}: testuser, test@test.com>")
    
    def  test_is_following_and_is_followed(self):
        u1 = User(
            email="test@test.com",
            username="testuser1",
            password="HASHED_PASSWORD"
        )

        u2 = User(
            email="example@test.com",
            username="testuser2",
            password="something"
        )

        with app.app_context():
            db.session.add(u1)
            db.session.add(u2)
            db.session.commit()
            new_u1_1 = User.query.filter(User.email == "test@test.com").first()
            new_u2_1 = User.query.filter(User.email == "example@test.com").first()

        follow_1 = Follows(
            user_being_followed_id=new_u2_1.id,
            user_following_id=new_u1_1.id
        )

        with app.app_context():
            db.session.add(follow_1)
            db.session.commit()
            new_u1_2 = User.query.filter(User.email == "test@test.com").first()
            new_u2_2 = User.query.filter(User.email == "example@test.com").first()

            # Returns true (user 1 is following user 2)
            self.assertTrue(new_u1_2.is_following(new_u2_2))
            # Returns false (user 2 is not following user 1)
            self.assertFalse(new_u2_2.is_following(new_u1_2))

            # Returns false (user 1 is not being followed by user 2)
            self.assertFalse(new_u1_2.is_followed_by(new_u2_2))
            # Returns true (user 2 is being followed by user 1)
            self.assertTrue(new_u2_2.is_followed_by(new_u1_2))
    
    def test_user_signup(self):
        with app.app_context():
            # Returns true if valid credentials are provided.
            new_user1 = User.signup(username="testuser1", email="test@test.com", password="secrets", image_url=User.image_url.default.arg)
            self.assertTrue(new_user1)
            # Needed to demonstrate test case further below
            db.session.commit()

            # Returns false if one or more credentials aren't provided
            new_user2 = User.signup(username="testuser2", email="example@test.com", password=None, image_url=User.image_url.default.arg)
            self.assertFalse(new_user2)

            # Returns false if the username provided already exists. 
            new_user3 = User.signup(username="testuser1", email="some@test.com", password="airplane", image_url=User.image_url.default.arg)
            self.assertFalse(new_user3)
    
    def test_user_authenticate(self):
        with app.app_context():
            u1 = User.signup(username="testuser1", email="test@test.com", password="HASHED_PASSWORD", image_url=User.image_url.default.arg)
            db.session.commit()
            
            # Returns true if both a valid username and password are provided.
            attempt_1 = User.authenticate(username="testuser1", password="HASHED_PASSWORD")
            self.assertTrue(attempt_1)
            
            # Returns false if an invalid password is provided.
            attempt_2 = User.authenticate(username="testuser1", password="something else")
            self.assertFalse(attempt_2)

            # Returns false if an invalid username is provided.
            attempt_3 = User.authenticate(username="testuser2", password="HASHED_PASSWORD")
            self.assertFalse(attempt_3)
    
    def test_user_update(self):
        with app.app_context():
            u1 = User.signup(username="testuser1", email="test@test.com", password="HASHED_PASSWORD", image_url=User.image_url.default.arg)
            db.session.commit()
            u1_extract = User.query.filter(User.username == "testuser1").first()
        
            
            User.update_user(user_id=u1_extract.id, username=None, email="some@test.com", image_url=None, header_image_url=None, bio=None)
            
            # Returns true if user instance has updated email
            updated_user = User.query.filter(User.email == "some@test.com").first()
            self.assertTrue(updated_user)
        
            # Returns false if user instance has previous email
            prior_user = User.query.filter(User.email == "test@test.com").first()
            self.assertFalse(prior_user)