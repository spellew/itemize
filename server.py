#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, request, redirect, abort, Response, url_for, \
    render_template, make_response, jsonify
from flask import session as login_session
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, scoped_session
from database import Base, User, Category, Item
from functools import wraps
import random
import string
import json

FB_APP_ID = json.loads(open('fb_client_secrets.json', 'r').read())['web'
        ]['app_id']
FB_APP_SECRET = json.loads(open('fb_client_secrets.json', 'r'
                           ).read())['web']['app_secret']

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2

app = Flask(__name__)

engine = create_engine('sqlite:///itemize.db')
Base.metadata.bind = engine

# Creates a database session, that"s always usable (no matter when created)
db_session = scoped_session(sessionmaker(bind=engine))


@app.teardown_request
def remove_db_session(arg=None):
    db_session.remove()


# checks if the user is in the database
def getUserID(facebook_id):
    try:
        user = \
            db_session.query(User).filter_by(facebook_id=facebook_id).one()
        return user.id
    except:
        return None

# We use the flask session to create and store our user in the database
def createUser(login_session):
    new_user = User(facebook_id=login_session['facebook_id'],
                    name=login_session['name'],
                    picture=login_session['picture'])
    db_session.add(new_user)
    db_session.commit()
    user = \
        db_session.query(User).filter_by(facebook_id=login_session['facebook_id'
            ]).one()
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
    return render_template('login.html', STATE=state,
                           FB_APP_ID=FB_APP_ID)

# Using the validated access_token we receive from the client,
# we send a request to the FB API for the user's basic information
# and profile picture. If the user isn't in our database, we store it,
# and the user's information is always stored in the flask session for later use.
@app.route('/fb_connect', methods=['POST'])
def fb_connect():
    if request.args.get('state') != login_session['state']:
        response = \
            make_response(json.dumps({'error': 'Invalid state parameter.'
                          }), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = request.data.decode('utf-8')
    url = \
        'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' \
        % (FB_APP_ID, FB_APP_SECRET, access_token)
    h = httplib2.Http()

    result = h.request(url, 'GET')[1]
    token = json.loads(result)['access_token']
    userinfo_url = \
        'https://graph.facebook.com/v3.2/me?access_token=%s&fields=name,id,email' \
        % token

    h = httplib2.Http()
    result = h.request(userinfo_url, 'GET')[1]
    data = json.loads(result)

    login_session['access_token'] = access_token
    login_session['facebook_id'] = data['id']
    login_session['name'] = data['name']

    picture_url = \
        'https://graph.facebook.com/%s/picture?type=large&redirect=0' \
        % login_session['facebook_id']

    h = httplib2.Http()
    result = h.request(picture_url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data['data']['url']

    user_id = getUserID(login_session['facebook_id'])

    if not user_id:
        user_id = createUser(login_session)

    login_session['id'] = user_id

    response = \
        make_response(json.dumps({'response': 'You are now logged in as %s.'
                       % login_session['name']}), 200)
    response.headers['Content-Type'] = 'application/json'
    return response

# We delete the user's information from our session and redirect
# them to the index
@app.route('/logout/', methods=['GET'])
def logout():
    success = fb_disconnect()
    if success:
        del login_session['access_token']
        del login_session['state']
        del login_session['facebook_id']
        del login_session['id']
        del login_session['name']
        del login_session['picture']
    return redirect(url_for('get_categories'))


def fb_disconnect():
    facebook_id = login_session['facebook_id']
    access_token = login_session['access_token']

    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
        % (facebook_id, access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'DELETE')[1])

    return 'success' in result and result['success']


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


@app.route('/', methods=['POST'])
@app.route('/categories/', methods=['POST'])
@auth.required
def new_category():
    if 'name' in request.form:
        try:
            new_category = Category(name=request.form['name'],
                                    user_id=1)
            db_session.add(new_category)
            db_session.commit()
            return redirect(url_for('get_items',
                            category_id=new_category.id))
        except Exception as e:
            print('Error: ')
            print(e)
            return abort(Response('An unexpected error occurred', 500))
    else:
        return abort(Response('Required form parameters are missing',
                     400))

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
                    setattr(category, arg, request.form[arg])
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
            db_session.query(Category).filter_by(id=category_id).one()
        items = \
            db_session.query(Item).filter_by(category_id=category_id).order_by(asc(Item.name)).all()
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


@app.route('/categories/<int:category_id>/', methods=['POST'])
@app.route('/categories/<int:category_id>/items/', methods=['POST'])
@auth.required
def new_item(category_id):
    if 'name' in request.form:
        try:
            new_item = Item(name=request.form['name'],
                            description=(request.form['description'
                            ] if 'description'
                            in request.form else None),
                            category_id=category_id, user_id=1)
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
                    setattr(item, arg, request.form[arg])
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
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)

