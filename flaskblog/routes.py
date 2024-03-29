import os
import secrets
from datetime import datetime

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_ckeditor import upload_fail, upload_success
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from PIL import Image
from werkzeug.utils import secure_filename

from flaskblog import app, bcrypt, db, mail
from flaskblog.forms import (
    LoginForm,
    PostForm,
    RegistrationForm,
    RequestResetForm,
    ResetPasswordForm,
    UpdateAccountForm,
)
from flaskblog.models import Category, Post, User


@app.route("/")
@app.route("/home")
def home():
    page = request.args.get("page", 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(
        page=page, per_page=5
    )
    post_per_category = []
    for category in Category.query.all():
        post_per_category.append(
            {"category": category.name, "posts": len(category.posts)}
        )
    return render_template(
        "home.html", posts=posts, categories=post_per_category
    )


@app.route("/about")
def about():
    return render_template("about.html", title="About")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_pw,
        )
        db.session.add(user)
        db.session.commit()
        flash(f"Account created for {form.username.data}!", "success")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and bcrypt.check_password_hash(
            user.password, form.password.data
        ):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            return (
                redirect(next_page) if next_page else redirect(url_for("home"))
            )
        else:
            flash(
                "Unsuccessful Login! Please check username and password",
                "danger",
            )
    return render_template("login.html", title="Login", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(
        app.root_path, "static/profile_pics", picture_fn
    )

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Your account has been updated", "success")
        return redirect(url_for("account"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    image_file = url_for(
        "static", filename="profile_pics/" + current_user.image_file
    )
    return render_template(
        "account.html", title="Account", image_file=image_file, form=form
    )


@app.route("/post/categories")
def categories():
    response = {"status": 404, "message": "Not Found", "data": []}
    categories = Category.query.all()

    if not categories:
        return response, response["status"]

    if len(categories) < 1:
        response["status"] = 204
        response["message"] = "No Content"
        response["data"] = []
        return response, response["status"]

    response["status"] = 200
    response["message"] = "Success"
    data = []
    for i in categories:
        data.append({"id": i.id, "name": i.name, "description": i.description})
    response["data"] = data

    return response, response["status"]


@app.route("/post/upload/images", methods=["POST"])
def upload_images():
    file = request.files.get("upload")
    extension = file.filename.split(".")[-1].lower()
    if extension not in ["jpg", "gif", "png", "jpeg"]:
        return upload_fail(message="Image only!")
    timestamp = datetime.now().time().strftime("%H%M%S")
    filename = f"{timestamp}_{secure_filename(file.filename)}"
    file.save(os.path.join(app.root_path, "static/upload/images", filename))
    url = url_for("post_image", filename=filename)
    return upload_success(url, filename=filename)


@app.route("/post/images/<path:filename>")
def post_image(filename):
    path = os.path.join(app.root_path, "static/upload/images")
    return send_from_directory(f"{path}", filename)


@app.route("/post/category/<string:category>")
def category_post(category):
    category = Category.query.filter_by(name=category).first_or_404()
    posts = category.posts

    post_per_category = []
    for c in Category.query.all():
        post_per_category.append({"category": c.name, "posts": len(c.posts)})

    return render_template(
        "category_post.html",
        posts=posts,
        total_post=len(posts),
        category=category,
        categories=post_per_category,
        title=f"{category.name} Posts",
    )


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            author=current_user,
        )
        for id in form.categories.data.split(","):
            category = Category.query.get(id)
            post.categories.append(category)
        db.session.add(post)
        db.session.commit()
        flash("Your post has been created!", "success")
        return redirect(url_for("home"))

    return render_template(
        "create_post.html", title="New Post", form=form, legend="New Post"
    )


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    post_per_category = []
    for category in Category.query.all():
        post_per_category.append(
            {"category": category.name, "posts": len(category.posts)}
        )
    return render_template(
        "post.html", title=post.title, post=post, categories=post_per_category
    )


@app.route("/post/<int:post_id>/update", methods=["GET", "POST"])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        category_id = form.categories.data.split(",")
        deleted_category = [
            c.id for c in post.categories.all() if str(c.id) not in category_id
        ]

        for id in deleted_category:
            category = Category.query.get(id)
            post.categories.remove(category)

        for id in category_id:
            if int(id) not in [c.id for c in post.categories.all()]:
                category = Category.query.get(id)
                post.categories.append(category)

        db.session.commit()
        flash("Your post has been updated!", "success")
        return redirect(url_for("post", post_id=post.id))
    elif request.method == "GET":
        form.title.data = post.title
        form.content.data = post.content
    return render_template(
        "create_post.html",
        title="Update Post",
        form=form,
        legend="Update Post",
        post=post,
    )


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Your post has been deleted!", "success")
    return redirect(url_for("home"))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get("page", 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    post_per_category = []
    for category in Category.query.all():
        post_per_category.append(
            {"category": category.name, "posts": len(category.posts)}
        )
    posts = (
        Post.query.filter_by(author=user)
        .order_by(Post.date_posted.desc())
        .paginate(page=page, per_page=5)
    )
    return render_template(
        "user_posts.html",
        posts=posts,
        user=user,
        title="User: " + user.username,
        categories=post_per_category,
    )


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message(
        "Password Reset Request",
        sender="itomikasa@gmail.com",
        recipients=[user.email],
    )
    msg.body = f"""To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simpy ignore this email
and no changes will be made
"""
    mail.send(msg)


@app.route("/reset_password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash(
            "An Email has been sent with instructions to reset your password.",
            "info",
        )
        return redirect(url_for("login"))
    return render_template(
        "reset_request.html", title="Reset Password", form=form
    )


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    user = User.verify_reset_token(token)
    if user is None:
        flash("That is an invalid or expired token", "warning")
        return redirect(url_for("reset_request"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        user.password = hashed_pw
        db.session.commit()
        flash("Your password has been reset", "success")
        return redirect(url_for("login"))
    return render_template(
        "reset_token.html", title="Reset Password", form=form
    )
