#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, request, redirect, abort, Response, url_for, \
    render_template, make_response, jsonify
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, scoped_session
from database import Base, Account, Category, Item
from functools import wraps
import httplib2
import requests
import random
import string
import json
import os

GOOGLE_CLIENT_ID = json.loads(
    open(os.path.dirname(os.path.realpath(__file__)) + '/' + 'g_client_secrets.json', 'r').read())['web']['client_id']

app = Flask(__name__)
app.secret_key = 'super_secret_key'

engine = create_engine('postgresql://catalog:itemize@localhost/itemize')
Base.metadata.bind = engine

# Creates a database session, that"s always usable (no matter when created)
db_session = scoped_session(sessionmaker(bind=engine))


@app.teardown_request
def remove_db_session(arg=None):
    db_session.remove()


# checks if the user is in the database
def getAccountID(email):
    try:
        user = \
            db_session.query(Account).filter_by(email=email).one()
        return user.id
    except Exception as e:
        return None


# We use the flask session to create and store our user in the database
def createAccount(login_session):
    new_user = Account(
      google_id=login_session['google_id'],
      picture=login_session['picture'],
      email=login_session['email']
    )
    db_session.add(new_user)
    db_session.commit()
    user = \
        db_session.query(Account).filter_by(
          google_id=login_session['google_id']
        ).one()
    return user.id


class auth:

    @staticmethod
    def required(f):

        @wraps(f)
        def wrapper(*args, **kwds):
            if 'id' not in login_session:
                return redirect(url_for('login'))

            return f(*args, **kwds)
        return wrapper


@app.route('/login/', methods=['GET'])
def login():
    state = ''.join(random.choice(string.ascii_uppercase
                    + string.digits) for x in range(32))
    login_session['state'] = state
    return render_template(
      'login.html',
      STATE=state,
      GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID
    )


# Using the validated access_token we receive from the client,
# we send a request to the FB API for the user's basic information
# and profile picture. If the user isn't in our database, we store it,
# and the user's information is always stored in the flask session
# for later use.
@app.route('/g_connect', methods=['POST'])
def g_connect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = \
            make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(os.path.dirname(os.path.realpath(__file__)) + '/' + 'g_client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1].decode('utf-8'))
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    google_id = credentials.id_token['sub']
    if result['user_id'] != google_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != GOOGLE_CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_google_id = login_session.get('google_id')
    if stored_access_token is not None:
        if google_id == stored_google_id:
            response = make_response(json.dumps(
              'Current user is already connected.'
            ), 200)
            response.headers['Content-Type'] = 'application/json'
            return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['google_id'] = google_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getAccountID(data['email'])

    if not user_id:
        user_id = createAccount(login_session)

    login_session['id'] = user_id

    response = \
        make_response(json.dumps(
          'You are now logged in as %s.' % login_session['email']
        ), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


# We delete the user's information from our session and redirect
# them to the index
@app.route('/logout/', methods=['GET'])
def logout():
    success = g_disconnect()
    if success:
        del login_session['access_token']
        del login_session['state']
        del login_session['google_id']
        del login_session['id']
        del login_session['email']
        del login_session['picture']
    return redirect(url_for('get_categories'))


def g_disconnect():
    access_token = login_session['access_token']

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    return result['status'] == '200'


@app.route('/', methods=['GET'])
@app.route('/categories/', methods=['GET'])
def get_categories():
    try:
        fmt = request.args.get('fmt')
        categories = \
            db_session.query(Category).order_by(asc(Category.name)).all()
        if fmt == 'json':
            return jsonify(categories=[category.serialize
                           for category in categories])
        else:
            return render_template('categories.html',
                                   categories=categories)
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


@app.route('/categories/JSON', methods=['GET'])
def get_categories_json():
    try:
        categories = \
            db_session.query(Category).order_by(asc(Category.name)).all()
        return jsonify(categories=[
          category.serialize for category in categories
        ])
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


@app.route('/', methods=['POST'])
@app.route('/categories/', methods=['POST'])
@auth.required
def new_category():
    if 'name' in request.form:
        if len(request.form['name']) >= 1:
            try:
                new_category = Category(name=request.form['name'],
                                        user_id=login_session['id'])
                db_session.add(new_category)
                db_session.commit()
                return redirect(url_for('get_items',
                                category_id=new_category.id))
            except Exception as e:
                print('Error: ')
                print(e)
                return abort(Response('An unexpected error occurred', 500))
        else:
            abort(Response('Parameters must not be empty', 400))
    else:
        return abort(Response('Required form parameters are missing', 400))


# If the form data from the client matches up to our accepted fields
# we'll change the record, if the user is authorized
@app.route('/categories/<int:category_id>/edit', methods=['PUT'])
@app.route('/categories/<int:category_id>/items/edit', methods=['PUT'])
@auth.required
def edit_category(category_id):
    try:
        category = \
            db_session.query(Category).filter_by(id=category_id).one()
        allowed_edits = ('name', )
        if login_session['id'] == category.user_id:
            for arg in request.form:
                if arg in allowed_edits:
                    if len(request.form[arg]) >= 1:
                        setattr(category, arg, request.form[arg])
                    else:
                        return abort(Response(
                          'Parameters must not be empty',
                          400
                        ))
            db_session.add(category)
            db_session.commit()
            return redirect(url_for('get_items',
                            category_id=category_id))
        else:
            return abort(Response('Unauthorized access', 401))
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


# We get the resource by id and delete it, if the user is authorized
@app.route('/categories/<int:category_id>/delete', methods=['DELETE'])
@app.route('/categories/<int:category_id>/items/delete',
           methods=['DELETE'])
@auth.required
def delete_category(category_id):
    try:
        category = \
            db_session.query(Category).filter_by(id=category_id).one()
        if login_session['id'] == category.user_id:
            items = \
                db_session.query(Item).filter_by(category_id=category_id).all()
            db_session.delete(category)
            for item in items:
                db_session.delete(item)
            db_session.commit()
            return redirect(url_for('get_categories'))
        else:
            return abort(Response('Unauthorized access', 401))
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


# If the url contains "?fmt=json" we serve a json containing the records,
# if not we serve an html page
@app.route('/categories/<int:category_id>/', methods=['GET'])
@app.route('/categories/<int:category_id>/items/', methods=['GET'])
def get_items(category_id):
    try:
        fmt = request.args.get('fmt')
        category = \
            db_session.query(Category).filter_by(
              id=category_id
            ).one()
        items = \
            db_session.query(Item).filter_by(
              category_id=category_id
            ).order_by(asc(Item.name)).all()
        if fmt == 'json':
            return jsonify(category=category.serialize,
                           items=[item.serialize for item in items])
        else:
            return render_template('category.html', category=category,
                                   items=items)
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


@app.route('/categories/<int:category_id>/JSON', methods=['GET'])
@app.route('/categories/<int:category_id>/items/JSON', methods=['GET'])
def get_items_json(category_id):
    try:
        category = \
            db_session.query(Category).filter_by(id=category_id).one()
        items = \
            db_session.query(Item).filter_by(
              category_id=category_id
            ).order_by(asc(Item.name)).all()
        serial = category.serialize.copy()
        serial['items'] = [item.serialize for item in items]
        return jsonify(
          category=serial
        )
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


@app.route('/categories/<int:category_id>/', methods=['POST'])
@app.route('/categories/<int:category_id>/items/', methods=['POST'])
@auth.required
def new_item(category_id):
    if 'name' in request.form:
        if len(request.form['name']) >= 1:
            try:
                new_item = Item(
                  name=request.form['name'],
                  description=(
                    request.form[
                      'description'
                    ] if 'description' in request.form else None
                  ),
                  category_id=category_id,
                  user_id=login_session['id']
                )
                db_session.add(new_item)
                db_session.commit()
                return redirect(url_for('get_item',
                                category_id=category_id,
                                item_id=new_item.id))
            except Exception as e:
                print('Error: ')
                print(e)
                return abort(Response('An unexpected error occurred', 500))
        else:
            return abort(Response(
              'Parameters must not be empty',
              400
            ))
    else:
        return abort(Response('Required form parameters are missing',
                     400))


@app.route('/categories/<int:category_id>/items/<int:item_id>/',
           methods=['GET'])
def get_item(category_id, item_id):
    try:
        fmt = request.args.get('fmt')
        category = \
            db_session.query(Category).filter_by(id=category_id).one()
        item = db_session.query(Item).filter_by(id=item_id).one()
        if fmt == 'json':
            return jsonify(item=item.serialize)
        else:
            return render_template('item.html', category=category,
                                   item=item)
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


@app.route('/categories/<int:category_id>/items/<int:item_id>/JSON',
           methods=['GET'])
def get_item_json(category_id, item_id):
    try:
        category = \
            db_session.query(Category).filter_by(id=category_id).one()
        item = db_session.query(Item).filter_by(id=item_id).one()
        return jsonify(item=item.serialize)
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


@app.route('/categories/<int:category_id>/items/<int:item_id>/edit',
           methods=['PUT'])
@auth.required
def edit_item(category_id, item_id):
    try:
        item = db_session.query(Item).filter_by(id=item_id).one()
        if login_session['id'] == item.user_id:
            allowed_edits = ('name', 'description')
            for arg in request.form:
                if arg in allowed_edits:
                    if arg == 'name':
                        if len(request.form['name']) >= 1:
                            setattr(item, arg, request.form[arg])
                        else:
                            return abort(Response(
                              'Parameters must not be empty',
                              400
                            ))
            db_session.add(item)
            db_session.commit()
            return redirect(url_for('get_item',
                            category_id=category_id, item_id=item_id))
        else:
            return abort(Response('Unauthorized access', 401))
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


@app.route('/categories/<int:category_id>/items/<int:item_id>/delete',
           methods=['DELETE'])
@auth.required
def delete_item(category_id, item_id):
    try:
        item = db_session.query(Item).filter_by(id=item_id).one()
        if login_session['id'] == item.user_id:
            db_session.delete(item)
            db_session.commit()
            return redirect(url_for('get_items',
                            category_id=category_id))
        else:
            return abort(Response('Unauthorized access', 401))
    except Exception as e:
        print('Error: ')
        print(e)
        return abort(Response('An unexpected error occurred', 500))


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
