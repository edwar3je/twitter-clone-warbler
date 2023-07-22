import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Likes, Follows

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.is_submitted() and form.validate():
        try:
            with app.app_context():

                # For some reason, the form can create a user instance, but doesn't properly redirect
                user = User.signup(
                    username=form.username.data,
                    password=form.password.data,
                    email=form.email.data,
                    image_url=form.image_url.data or User.image_url.default.arg,
                )
                print('---------------------------')
                print(user.username)
                print(user.password)
                print(user.email)
                print(user.image_url)
                print('---------------------------')
                db.session.add(user)
                db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        with app.app_context():
            new_user = User.query.filter(User.username == form.username.data).first()
        do_login(new_user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.is_submitted() and form.validate():
        with app.app_context():
            user = User.authenticate(form.username.data,
                                    form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            print('-------------------')
            print(session[CURR_USER_KEY])
            print('-------------------')
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS
    if session[CURR_USER_KEY]:

        do_logout()

        flash("You have successfully logged out of your account!", "success")
        return redirect("/login")


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    
    likes = Likes.query.filter(Likes.user_id == user_id).all()

    other_likes = Likes.query.filter(Likes.user_id == session[CURR_USER_KEY]).all()
    other_likes_ids = [other_like.message_id for other_like in other_likes]

    return render_template('users/show.html', user=user, messages=messages, likes=likes, other_likes=other_likes_ids)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    likes = Likes.query.filter(Likes.user_id == user_id).all()

    return render_template('users/following.html', user=user, likes=likes)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    likes = Likes.query.filter(Likes.user_id == user_id).all()

    return render_template('users/followers.html', user=user, likes=likes)


@app.route('/users/<int:user_id>/likes')
def show_likes(user_id):
    """Show list of posts that the user has liked."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    
    user = User.query.get_or_404(user_id)

    liked = Likes.query.filter(Likes.user_id == user.id).all()
    liked_ids = [like.message_id for like in liked]
    liked_posts = Message.query.filter(Message.id.in_(liked_ids))

    other_likes = Likes.query.filter(Likes.user_id == session[CURR_USER_KEY]).all()
    other_likes_ids = [other_like.message_id for other_like in other_likes]

    return render_template('users/likes.html', user=user, messages=liked_posts, likes=liked, other_likes=other_likes_ids)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    # IMPLEMENT THIS
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    
    form = UserEditForm()
    current_user_id = session[CURR_USER_KEY]
    with app.app_context():
        current_user = User.query.get(current_user_id)

    # If the request is a post request and the password is correct, any form data that is truthy will be used to update the user instance.
    if form.is_submitted() and form.validate():
        with app.app_context():
            # If the password is correct
            if User.authenticate(current_user.username, form.password.data):
                User.update_user(user_id=current_user_id, username=form.username.data, email=form.email.data, image_url=form.image_url.data, header_image_url=form.header_image_url.data, bio=form.bio.data)
                flash("You successfully updated your profile information!", "success")
                return redirect(f"/users/{current_user_id}")
            # If the password is incorrect
            else:
                flash("The password provided was invalid.", "danger")
                return redirect("/users/profile")
    
    return render_template("users/edit.html", user=current_user, form=form)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    
    # Delete every reference to a follower or accounts being followed
    Follows.query.filter(Follows.user_being_followed_id == session[CURR_USER_KEY]).delete()
    Follows.query.filter(Follows.user_following_id == session[CURR_USER_KEY]).delete()
    db.session.commit()

    # Delete every message that was liked by the account
    Likes.query.filter(Likes.user_id == session[CURR_USER_KEY]).delete()
    db.session.commit()

    # Delete every message of the account that has been liked
    all_messages = Message.query.filter(Message.user_id == session[CURR_USER_KEY]).all()
    all_messages_ids = [message.id for message in all_messages]
    Likes.query.filter(Likes.message_id.in_(all_messages_ids)).delete()
    db.session.commit()

    # Delete every message that comes from the account
    Message.query.filter(Message.user_id == session[CURR_USER_KEY]).delete()
    db.session.commit()

    # Delete the profile and remove any information from session
    current_user = User.query.filter(User.id == session[CURR_USER_KEY]).first()
    
    db.session.delete(current_user)
    db.session.commit()

    session.pop()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.is_submitted() and form.validate():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)

    like = Likes.query.filter((Likes.user_id == session[CURR_USER_KEY]) & (Likes.message_id == message_id)).first()

    return render_template('messages/show.html', message=msg, like=like)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)

    if msg.user_id != session[CURR_USER_KEY]:
        flash("You can't delete another user's posts.", "danger")
        return redirect("/")
    
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# General routes for liking and unliking a post

@app.route('/users/add_like/<int:message_id>', methods=["POST"])
def like_message(message_id):
    """Like a message."""

    # redirects if the user isn't logged in
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    
    message_id = request.view_args["message_id"]
    msg = Message.query.get(message_id)
    current_user = User.query.get(session[CURR_USER_KEY])
    
    # redirects if the user attempts to like their own post
    if msg.user_id == current_user.id:
        flash("You can't like your own posts.", "danger")
        return redirect("/")
    
    # adds a new like instance (effectively "liking" a post) and redirects
    else:
        new_like = Likes(user_id=current_user.id, message_id=msg.id)
        db.session.add(new_like)
        db.session.commit()
        return redirect("/")

@app.route("/users/remove_like/<int:message_id>", methods=["POST"])
def unlike_message(message_id):
    """Un-like a message."""

    #redirects if the user isn't logged in
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    
    message_id = request.view_args["message_id"]
    msg = Message.query.get(message_id)
    current_user = User.query.get(session[CURR_USER_KEY])
    liked_message = Likes.query.filter((Likes.user_id == current_user.id) & (Likes.message_id == msg.id)).first()

    
    # redirects if the user attempt to un-like their own post
    if msg.user_id == current_user.id:
        flash("you can't un-like your own posts.", "danger")
        return redirect("/")
    
    # redirects if the user attempts to unlike a post that isn't liked
    if not liked_message:
        flash("You can't unlike a post that wasn't originally liked.", "danger")
        return redirect("/")
    
    # deletes liked_message instance from database and redirects
    else:
        db.session.delete(liked_message)
        db.session.commit()
        flash("You successfully removed a liked message.", "success")
        return redirect("/")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        # Extract the current user along with the ids of their following list.
        current_user = User.query.get(session[CURR_USER_KEY])
        followed_users = current_user.following
        followed_users_ids = [followed_user.id for followed_user in followed_users]
        # Append user's own id to end of list (easier than adding an extra condition on query statement)
        followed_users_ids.append(session[CURR_USER_KEY])
        # Send the last 100 messages from followers and self to home page.
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(followed_users_ids))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())
        
        messages_ids = [message.id for message in messages if message.user_id != current_user.id]
        liked_posts = Likes.query.filter(Likes.message_id.in_(messages_ids))
        likes = [like.message_id for like in liked_posts]

        return render_template('home.html', messages=messages, likes=likes)

    else:
        return render_template('home-anon.html')

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
