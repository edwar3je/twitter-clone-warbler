import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows, Likes

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

from app import app, CURR_USER_KEY

with app.app_context():
    db.create_all()

app.config['WTF_CSRF_ENABLED'] = False

class UserViewTestCase(TestCase):
    
    def setUp(self):
        with app.app_context():
            User.query.delete()
            Message.query.delete()
            Follows.query.delete()
            Likes.query.delete()

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
            db.session.add(message_4)
            db.session.commit()

            follow_1 = Follows(user_being_followed_id=testuser_extract2.id, user_following_id=testuser_extract1.id)
            db.session.add(follow_1)
            db.session.commit()

            follow_2 = Follows(user_being_followed_id=testuser_extract1.id, user_following_id=testuser_extract2.id)
            db.session.add(follow_2)
            db.session.commit()

            extract_message1 = Message.query.filter(Message.text == "First other message.").first()
            extract_message2 = Message.query.filter(Message.text == "First message.").first()

            like_1 = Likes(user_id=testuser_extract1.id, message_id=extract_message1.id)
            db.session.add(like_1)
            db.session.commit()

            like_2 = Likes(user_id=testuser_extract2.id, message_id=extract_message2.id)
            db.session.add(like_2)
            db.session.commit()
    
    def test_show_all_users(self):
        """If logged in, displays a page of all the users."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
        
            resp = c.get("/users")
            html = resp.get_data(as_text=True)

            # response should successfully render a template (not redirect)
            self.assertEqual(resp.status_code, 200)

            # response should display user's own account
            self.assertIn("testuser", html)

            # response should dislplay other users accounts
            self.assertIn("testuser2", html)
            
            # response should not display non-existent accounts
            self.assertNotIn("testuser6", html)
    
    def test_show_user_profile(self):
        """If logged in, displays a page of the user's profile.
        The profile should show every message created by the user.
        Additionally, if it's the current user's profile, it should
        display the option to either edit or delete their profile."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            other_user = User.query.filter(User.username == "testuser2").first()

        # For current user's profile
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
        
            resp = c.get(f"/users/{current_user.id}")
            html = resp.get_data(as_text=True)

            # response should successfully render a template (not redirect)
            self.assertEqual(resp.status_code, 200)

            # the current user's page should only display their messages.
            self.assertIn("First message.", html)
            self.assertNotIn("First other message.", html)

            # the current user's page should allow them to edit or delete their profile
            self.assertIn("Edit Profile", html)
            self.assertIn("Delete Profile", html)
        
        # For other user's profile
        with self.client as d:
            with d.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp2 = d.get(f"/users/{other_user.id}")
            html2 = resp2.get_data(as_text=True)

            # response should successfully render a template (not redirect)
            self.assertEqual(resp2.status_code, 200)

            # the user's page should only display their messages.
            self.assertIn("First other message.", html2)
            self.assertNotIn("First message.", html2)

            # the current user should not be allowed to edit and/or delete another user's profile
            self.assertNotIn("Edit Profile", html2)
            self.assertNotIn("Delete Profile", html2)
    
    def test_following_page(self):
        """If logged on, should display a page of all the accounts the user is following.
        If it is the profile of the current_user, it should allow the user to unfollow an account."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            other_user = User.query.filter(User.username == "testuser2").first()

        # For current user's profile 
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp1 = c.get(f"/users/{current_user.id}/following")
            html1 = resp1.get_data(as_text=True)

            # response should successfully render a template (not redirect)
            self.assertEqual(resp1.status_code, 200)

            # the user's page should only display accounts they follow
            self.assertIn("testuser2", html1)
            self.assertNotIn("testuser3", html1)

            # the current user's page should allow them to unfollow
            self.assertIn("Unfollow", html1)
        
        # For other user's profile
        with self.client as d:
            with d.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp2 = d.get(f"/users/{other_user.id}/following")
            html2 = resp2.get_data(as_text=True)

            # response should successfully render a template (not redirect)
            self.assertEqual(resp2.status_code, 200)

            # the user's page should only display accounts they follow
            self.assertIn("testuser", html2)
            self.assertNotIn("testuser3", html2)

            # if the current user accesses another page and it has their account
            # it should not allow them to follow or unfollow themselves
            # (Need to user angled brackets, because other words like "Followers" are used in the page)
            self.assertNotIn(">Follow<", html2)
    
    def test_followers_page(self):
        """If logged on, should display a page containing all of the accounts that follow the user."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            other_user = User.query.filter(User.username == "testuser2").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id

            resp1 = c.get(f"/users/{current_user.id}/followers")
            html1 = resp1.get_data(as_text=True)

            # Should successfully render a template
            self.assertEqual(resp1.status_code, 200)

            # Should only display accounts that are following the user
            self.assertIn("testuser2", html1)
            self.assertNotIn("testuser3", html1)

        with self.client as d:
            with d.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp2 = d.get(f"/users/{other_user.id}/followers")
            html2 = resp2.get_data(as_text=True)

            # Should successfully render a template
            self.assertEqual(resp1.status_code, 200)

            # Should only display account that are following the user
            self.assertIn("testuser", html2)
            self.assertNotIn("testuser3", html2)

    def test_likes_page(self):
        """If logged in, displays the user's liked posts (from other accounts).
        The current user should not be allowed to like (or unlike) their own posts."""
    
        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            other_user = User.query.filter(User.username == "testuser2").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp1 = c.get(f"/users/{current_user.id}/likes")
            html1 = resp1.get_data(as_text=True)

            # Should successfully render a template
            self.assertEqual(resp1.status_code, 200)

            # Should only display posts that the user has liked
            self.assertIn("First other message.", html1)
            self.assertNotIn("Yet another message.", html1)

            # The current user should be able to unlike posts (<svg> is only used for unliking)
            self.assertIn("/users/remove_like/", html1)
        
        with self.client as d:
            with d.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp2 = d.get(f"/users/{other_user.id}/likes")
            html2 = resp2.get_data(as_text=True)

            # Should successfully render a template
            self.assertEqual(resp2.status_code, 200)

            # Should only display posts that the user has liked
            self.assertIn("First message.", html2)
            self.assertNotIn("Yet another message.", html2)
            
            # The current user should not be able to like (or unlike) their own messages
            self.assertNotIn("/users/add_like/", html2)
            self.assertNotIn("/users/remove_like/", html2)
    
    def test_add_like(self):
        """Logged in users should be allowed to like any post that isn't theirs."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            
            message_1 = Message.query.filter(Message.text == "Yet another message.").first()
            message_2 = Message.query.filter(Message.text == "First message.").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp1 = c.post(f"/users/add_like/{message_1.id}")
            html1 = resp1.get_data(as_text=True)

            # A successful response should redirect the user
            self.assertEqual(resp1.status_code, 302)

            # A successful like should increase the length of all likes for that user
            self.assertEqual(len(Likes.query.filter(Likes.user_id == current_user.id).all()), 2)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp2 = c.post(f"/users/add_like/{message_2.id}")
            html2 = resp2.get_data(as_text=True)

            # An unsuccessful response should redirect the user
            self.assertEqual(resp2.status_code, 302)

            # An unsuccessful response should not increase the length of all likes for that user
            self.assertEqual(len(Likes.query.filter(Likes.user_id == current_user.id).all()), 2)
    
    def test_remove_like(self):
        """Logged in users should be allowed to remove a like from any post they have previously liked"""

        with app.app_context():
            user = User.query.filter(User.username == "testuser").first()
            message_1 = Message.query.filter(Message.text == "Yet another message.").first()
            message_2 = Message.query.filter(Message.text == "First message.").first()
            
            new_like = Likes(user_id=user.id, message_id=message_1.id)
            db.session.add(new_like)
            db.session.commit()

            current_user_id = user.id
            message_1_id = message_1.id
            message_2_id = message_2.id
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user_id
            
            resp1 = c.post(f"/users/remove_like/{message_1_id}")
            
            # A successful response should redirect the user 
            self.assertEqual(resp1.status_code, 302)

            # A successful remove-like should decrease the length of all likes for that user
            self.assertEqual(len(Likes.query.filter(Likes.user_id == current_user_id).all()), 1)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user_id
            
            resp2 = c.post(f"/users/remove_like/{message_2_id}")

            # Attempting to unlike your own post should redirect the user
            self.assertEqual(resp2.status_code, 302)

            # Attempting to remove a like from your own post should not change the overall likes
            self.assertEqual(len(Likes.query.filter(Likes.user_id == current_user_id).all()), 1)
    
    def test_follow_user(self):
        """Logged in user should be able to follow another account."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            other_user = User.query.filter(User.username == "testuser3").first()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id 
            
            resp1 = c.post(f"/users/follow/{other_user.id}")

            # A successful response should redirect the user
            self.assertEqual(resp1.status_code, 302)

            # The user should now appear as an account you are following
            self.assertTrue(Follows.query.filter(Follows.user_being_followed_id == other_user.id).first())
        
    def test_unfollow_user(self):
        """Logged in user should be able to unfollow an account they are currently following."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
            other_user = User.query.filter(User.username == "testuser2").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp1 = c.post(f"/users/stop-following/{other_user.id}")

            # A successful response should redirect the user
            self.assertEqual(resp1.status_code, 302)

            # The user should not appear as an account the user is following
            self.assertFalse(Follows.query.filter(Follows.user_being_followed_id == other_user.id).first())
    
    def test_get_edit_profile(self):
        """Logged in user should be able to access a page that allows them to edit their profile information."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp = c.get("/users/profile")
            html = resp.get_data(as_text=True)

            # A successful response should render a template
            self.assertEqual(resp.status_code, 200)

            # The page should have the user's name along with inputs for the form
            self.assertIn("testuser", html)
            self.assertIn("<input", html)
    
    """def test_post_edit_profile(self):
        #Logged in user should be able to update their profile information.

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
            
            resp1 = c.post("/users/profile", data={"user_id": f"{current_user.id}", "username": "None", "password": "testuser", "email": "None", "image_url": "None", "header_image_url": "None", "bio": "Just some guy."})

            # A successful response should redirect the user
            self.assertEqual(resp1.status_code, 302)

            # Providing the proper credentials should update the user's bio
            self.assertTrue(User.query.filter(User.bio == "Just some guy.").first())

            resp2 = c.post("/users/profile", data={"user_id": f"{current_user.id}", "username": None, "password": "something else", "email": None, "image_url": None, "header_image_url": None, "bio": "Just another guy."})

            # An unsuccessful response should redirect the user
            self.assertEqual(resp2.status_code, 302)

            # Providing invalid credentials should not update the user's bio
            self.assertFalse(User.query.filter(User.bio == "Just another guy.").first())"""
    
    def test_delete_profile(self):
        """Logged in user should be able to delete their own profile."""

        with app.app_context():
            current_user = User.query.filter(User.username == "testuser").first()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = current_user.id
        
            resp = c.post("/users/delete")

            # Successful response should redirect user (unsuccessful)
            self.assertEqual(resp.status_code, 302)

            # The user account should no longer be present
            self.assertFalse(User.query.filter(User.username == "testuser").first())