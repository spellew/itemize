from flask import Flask, request, redirect, abort, Response, url_for, render_template
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, scoped_session
from database import Base, User, Category, Item

app = Flask(__name__)

engine = create_engine("sqlite:///itemize.db")
Base.metadata.bind = engine

# Creates a database session, that"s always usable (no matter when created)
db_session = scoped_session(sessionmaker(bind = engine))

@app.teardown_request
def remove_db_session(arg = None):
  db_session.remove()

@app.route("/", methods = ["GET", "POST"])
@app.route("/categories/", methods = ["GET", "POST"])
def categories():
  if request.method == "POST":
    if "name" in request.form:
      try:
        new_category = Category(name = request.form["name"], user_id = 1)
        db_session.add(new_category)
        db_session.commit()
        return redirect(url_for("update_categories", category_id = new_category.id))
      except Exception as e:
        print("Error: ")
        print(e)
        return abort(Response("An unexpected error occurred", 500))
    else:
      return abort(Response("Required form parameters are missing", 400))
  else:
    try:
      categories = db_session.query(Category).order_by(asc(Category.name,)).all()
      return render_template("categories.html", categories = categories)
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))


@app.route("/categories/<int:category_id>/", methods = ["GET", "PUT", "DELETE"])
@app.route("/categories/<int:category_id>/items/", methods = ["GET"])
def update_categories(category_id):
  if request.method == "PUT":
    try:
      category = db_session.query(Category).filter_by(id = category_id).one()
      allowed_edits = ("name",)
      for arg in request.form:
        if arg in allowed_edits:
          setattr(category, arg, request.form[arg])
      db_session.add(category)
      db_session.commit()
      return redirect(url_for("update_categories", category_id = category_id))
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))
  elif request.method == "DELETE":
    try:
      category = db_session.query(Category).filter_by(id = category_id).one()
      items = db_session.query(Item).filter_by(category_id = category_id).all()
      db_session.delete(category)
      for item in items:
        db_session.delete(item)
      db_session.commit()
      return redirect(url_for("categories"))
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))
  else:
    try:
      category = db_session.query(Category).filter_by(id = category_id).one()
      items = db_session.query(Item).filter_by(category_id = category_id).order_by(asc(Item.name,)).all()
      return render_template("category.html", category = category, items = items)
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))

@app.route("/categories/<int:category_id>/", methods = ["POST"])
@app.route("/categories/<int:category_id>/items/", methods = ["POST"])
def new_items(category_id):
  if "name" in request.form:
    try:
      new_item = Item(name = request.form["name"], description = request.form["description"] if "description" in request.form else None, category_id = category_id, user_id = 1)
      db_session.add(new_item)
      db_session.commit()
      return redirect(url_for("update_items", category_id = category_id, item_id = new_item.id))
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))
  else:
    return abort(Response("Required form parameters are missing", 400))


@app.route("/categories/<int:category_id>/items/<int:item_id>/", methods = ["GET", "PUT", "DELETE"])
def update_items(category_id, item_id):
  if request.method == "PUT":
    try:
      item = db_session.query(Item).filter_by(id = item_id).one()
      allowed_edits = ("name", "description")
      for arg in request.form:
        if arg in allowed_edits:
          setattr(item, arg, request.form[arg])
      db_session.add(item)
      db_session.commit()
      return redirect(url_for("update_items", category_id = category_id, item_id = item_id))
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))
  elif request.method == "DELETE":
    try:
      item = db_session.query(Item).filter_by(id = item_id).one()
      db_session.delete(item)
      db_session.commit()
      return redirect(url_for("update_categories", category_id = category_id))
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))
  else:
    try:
      category = db_session.query(Category).filter_by(id = category_id).one()
      item = db_session.query(Item).filter_by(id = item_id).one()
      return render_template("item.html", category = category, item = item)
    except Exception as e:
      print("Error: ")
      print(e)
      return abort(Response("An unexpected error occurred", 500))



if __name__ == "__main__":
  app.secret_key = "super_secret_key"
  app.debug = True
  app.run(host="0.0.0.0", port=5000)