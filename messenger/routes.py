from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from messenger.forms import (LoginForm, RegistrationForm, EmailForm, PasswordForm, 
    ContactForm, EditProfileForm, ReportBugForm, NewGroupForm
)
from messenger.models import User, Password, BlockedUsers
from messenger import app, db, flow, GOOGLE_CLIENT_ID, socketio, REFRESH_TOKEN_EXPIRATION, ACCESS_TOKEN_EXPIRATION, redis
from messenger.utilities import (
    hash_password, send_email_confirmation, get_chat_history, handle_message, get_chats, add_members, delete_avatar_by_id, see_unseen_messages,
    handle_create_chat, search, get_chat_info, process_upload_image, renew_online_user, get_chat_data, change_chat_data, get_user_static_avatar_url,
    delete_message, handle_forwarding, see_peers_messages, delete_chat, block_user, is_chat_exist, is_member, get_random_avatar, get_members, get_mongo_data_avatar
)
from functools import wraps
import jwt
from datetime import timedelta, datetime
import requests
from pip._vendor import cachecontrol
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from flask_socketio import Namespace, emit
from werkzeug.datastructures import MultiDict
import json



def redirect_to_email_confirmation(user, route_function, comment='Confirmation', next_page=None):
    url = next_page if next_page else url_for('home')

    email_token = create_jwt_token(user.user_id, timedelta(minutes=10))
    redirect_uri = url_for(route_function, token=email_token, next_page=url, _external=True)
    email = user.email
    #print('call a function to send the email message', email, redirect_uri)
    send_email_confirmation(email, redirect_uri, comment)

def get_from_redis(key):
    res = redis.get(key)
    #print('REIDS', res)
    return res

def is_token_valid(token):
    sign = get_from_redis(token)
    if sign == 0:
        return 0 # deleted
    elif sign is not None:
        return sign # user from User db
    return None

def create_jwt_token(user_id: int, expiration_time, refresh=False) -> str:
    expiration_date = datetime.now() + expiration_time
    try:
        token = jwt.encode({'sub': user_id, 'exp': expiration_date}, app.secret_key, algorithm='HS256')
        if refresh: redis.set(token, user_id, ex=expiration_time)
    except Exception as e:
        #print('Error while creating jwt token: ', e)
        return None
    return token

def decode_jwt_token(token: str, secret_key=app.secret_key, algorithms=['HS256'], refresh=False) -> int:
    try:
        #print('The got token to decode is:', token)
        sign = is_token_valid(token)
        # Maybe, in my case I could utilize the fact that sign is user_id
        if not sign and not (not refresh and sign is None): 
            return 'invalid'
        user_id = jwt.decode(token, secret_key, algorithms)['sub']
        #print('User id is successfully decoded. Decorator.', user_id)
        user = User.query.get(user_id)
        if not user:
            return 'invalid'
    except jwt.ExpiredSignatureError:
        #print('The token is expired. ')
        return 'expired'
    except Exception as e:
        #print('We have an error on getting data from jwt token. ', e)
        return 'invalid'
    
    return user
    

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('access-token')
        current_route = request.path
        #print(current_route)
        ##print('The gotten args are:', *args, **kwargs)
        for arg in [*args]:
            #print('Got argument:', arg)
            pass
        #print(request.args, *args)
        refresh_redirect = redirect(url_for('refresh', next_page=current_route, args=[*args]))
        if not token:
            #print('There is no access token in cookies. ')
            # Note it's possible to redirect like this
            return refresh_redirect
        
        response = decode_jwt_token(token)
        #print('Decorator. The returned response is:', response)
        if response == 'invalid':
            flash("Invalid token. Please log in again.", "info")
            response = redirect(url_for('login'))
            response.delete_cookie('access-token')
            return response
        
        elif response == 'expired':
            return refresh_redirect
        
        else:
            #print('Tokens are okay!')
            # Response is a user
            renew_online_user(response)
            return f(response, *args, **kwargs)
            

    return decorated


class ChatSockets(Namespace):
    def __init__(self, namespace, chat_id):
        # To ensure initialization
        super().__init__(namespace)
        self.chat_id = chat_id
        #print('Socket on server has been initialized. Id is:', self.chat_id, type(self.chat_id))

    def on_connect(self):
        #print(f'Client connected to namespace {self.namespace}')
        emit('connect', 'You\'re connected successfully. ', namespace=self.namespace)

    def on_disconnect(self):
        #print(f'Client disconnected from namespace {self.namespace}')
        emit('disconnect', 'You\'re disconnected', namespace=self.namespace)

    @jwt_required
    # There will always be user and only user with jwt token
    def on_new_message(user, self, message):
        #print(self.namespace, self)
        #print('The author is: ' + user.first_name)
        #print(message)
        # Self message is different by style
        # TODO: maybe, I could handle mine on the client or I shouldn't? it probably will take me to slice the string which is unconvenient and overkill.
        # Returning multiple messages is complex too because we will need to handle messages from collections which only need one message per request.
        
        # False because we need nothing with mine. 
        # When true that means deletion of previous avatar
        html_message, _, id = handle_message(self.chat_id, message, 'mine', user, None)
        emit('add_new_message', {
            'message': html_message, 'mine': "mine", 'is_prev_message_mine': False}, 
        namespace=self.namespace)
        
        peer_html_message, is_prev_message_mine, _ = handle_message(self.chat_id, message, '', user, id)
        emit('add_new_message', {
            'message': peer_html_message, 'mine': "", 'is_prev_message_mine': is_prev_message_mine}, 
        namespace=self.namespace, broadcast=True, include_self=False)

        renew_online_user(user)
        

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'access-token' in request.cookies:
        return redirect(url_for('home'))

    form_type = request.form.get('form_type')
    
    # TODO many lines and duplicates
    form = LoginForm()
    email_form = EmailForm()
    if form_type == "update" and email_form.validate_on_submit():
        #print('Starting updating password. Login email. ', email_form.email.data, form.email.data)
        user = email_form.validate_user()
        if not user:
            flash('The email or password is incorrect. Please try again. ', category='danger')
            return render_template('login.html', form=form, email_form=email_form, title='Login')
        
        flash('The email to change the password has been sent.', category='info')
        redirect_to_email_confirmation(user, 'forgot_password', 'Modifying', request.args.get('next'))


    elif form_type == "login" and form.validate_on_submit():
        user = form.validate_user()
        if not user:
            flash('The email or password is incorrect. Please try again. ', category='danger')
            return render_template('login.html', form=form, email_form=email_form, title='Login')
        
        password = user.hashed_password[0]
        hashed_password, _ = hash_password(form.password.data, password.salt)
        if hashed_password != password.hashed_password:
            flash('The email or password is incorrect. Please try again. ', category='danger')
            return render_template('login.html', form=form, email_form=email_form, title='Login')

        flash('The email has been sent to your address!', category='success')
        redirect_to_email_confirmation(user, 'login_confirmation', 'Confirmation', request.args.get('next'))
        
        
    return render_template('login.html', form=form, email_form=email_form, title='Login')

@app.route('/login/confirmation/<string:token>', methods=['POST', 'GET'])
def login_confirmation(token):
    next_page = request.args.get('next_page', url_for('home'))
    #print('message is received', token, next_page)

    response = decode_jwt_token(token)
    if response in ['invalid', 'expired']:
        #print('There is no user with this id. ')
        flash('Invalid token. Please try again.', "danger")
        return redirect(url_for('login'))
    
    user_id = response.user_id
    
    access_token = create_jwt_token(user_id, ACCESS_TOKEN_EXPIRATION)
    refresh_token = create_jwt_token(user_id, REFRESH_TOKEN_EXPIRATION, refresh=True)

    # httpponly for secureity: disallow js 
    response = redirect(next_page)
    response.set_cookie('access-token', access_token, httponly=True)
    response.set_cookie('refresh-token', refresh_token, httponly=True)
        
    return response


@app.route('/auth/google')
def auth_google():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

@app.route('/auth/google/callback')
def callback():
    flow.fetch_token(authorization_response=request.url)

    state = request.args.get('state')
    if not(session.get('state') == state):
        return url_for('login', message='Invalid state. Please try again.')
    
    credentials = flow.credentials
    
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = Request(session=cached_session)

    try:
        user_info = id_token.verify_oauth2_token(
            id_token=credentials.id_token,
            audience=GOOGLE_CLIENT_ID,
            request=token_request
        )
    except Exception as e:
        #print(e)
        return url_for('login', message='Invalid token. Please try again.')

    #print(user_info)
    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    # TODO here's probably should be a refresh token function
    if not user:
        avatar = get_random_avatar()
        user = User(first_name=user_info['given_name'], last_name=user_info['family_name'], email=email, avatar=avatar, bio="", last_seen="#")
        db.session.add(user)
        db.session.commit()

    access_token = create_jwt_token(user.user_id, ACCESS_TOKEN_EXPIRATION)
    refresh_token = create_jwt_token(user.user_id, REFRESH_TOKEN_EXPIRATION, refresh=True)

    print(access_token, refresh_token)

    # TODO is there any way not to replicate this?
    print(url_for('home'))
    response = redirect('https://messenger-s3fg.onrender.com/home')
    print(response, url_for('home'))
    response.set_cookie('access-token', access_token, httponly=True)
    response.set_cookie('refresh-token', refresh_token, httponly=True)

    return response


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if 'access-token' in request.cookies:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        response = form.validate_user()
        if response:
            flash('The account with this email already exists. Please choose another one.', category='danger')
            return render_template('registration.html', form=form, title='Registration')
        
        first_name, last_name, email, password = form.first_name.data, form.last_name.data, form.email.data, form.password.data
        avatar = get_random_avatar()
        user = User(first_name=first_name, last_name=last_name, email=email, avatar=avatar, bio="", last_seen="#")

        # NOTE we can use add and commit only with db.
        db.session.add(user)
        db.session.commit()

        renew_online_user(user) # this important because I have skipped last seen
        
        hashed_password, salt =  hash_password(password)
        
        # The problem why I cannot add them at one time is that user_id is not generated yet. So I need to add and commit db to perform this.
        password = Password(user_id=user.user_id, hashed_password=hashed_password, salt=salt)
        db.session.add(password)
        db.session.commit()
        flash("The account was successfully created. Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('registration.html', form=form, title='Registration')


@app.route('/refresh')
def refresh():
    # Here and only here I refresh my tokens
    # TODO: the only concern is would I lose my INITIAL args and kwargs from previous route?
    #print(request.args)
    current_path = request.args.get('next_page')
    invalid_message = "Invalid token. Please log in again."
    invalid_response = redirect(url_for('login'))
    invalid_response.delete_cookie('refresh-token')
    invalid_response.delete_cookie('access-token')
    try:
        refresh_token = request.cookies.get('refresh-token')
        #print('The refresh token is', refresh_token)
        response = decode_jwt_token(refresh_token, refresh=True)
        if response in ['invalid', 'expired']:
            #print('The refresh token is invalid.')
            flash(invalid_message, "info")
            return invalid_response
        #print('Started to refresh token...')
        user_id = response.user_id
        access_token = create_jwt_token(user_id, ACCESS_TOKEN_EXPIRATION)
        refresh_token = create_jwt_token(user_id, REFRESH_TOKEN_EXPIRATION, refresh=True)
        response = redirect(current_path) if current_path else make_response(jsonify({'current': True}), 200)
        response.set_cookie('access-token', access_token, httponly=True)
        response.set_cookie('refresh-token', refresh_token, httponly=True)
        #print('Refreshing token is completed. ')
    except Exception as e:
        #print('We have an error on getting data from jwt token while refreshing this. ', e)
        flash(invalid_message, "info")
        return invalid_response
    
    return response


@app.route('/logout')
@jwt_required
def logout(user):
    # Tokens cannot be expired cuz jwt_required
    tokens = [request.cookies.get('access-token'), request.cookies.get('refresh-token')]
    for token in tokens:
        if token:
            try: 
                expiration_date = jwt.decode(token, app.secret_key, algorithms=['HS256'])['exp']
                #print(expiration_date)
                redis.setex(token, expiration_date, 0)
            except Exception as e:
                #print('Failed to get expiration date of the token.', e)
                continue

    response = redirect(url_for('login'))
    response.delete_cookie('access-token', httponly=True)
    response.delete_cookie('refresh-token', httponly=True)
    return response


@app.route('/forgot_password/<string:token>', methods=['GET', 'POST'])
def forgot_password(token):
    response = decode_jwt_token(token)
    if response in ['invalid', 'expired'] or not User.query.get(response.user_id):
        #print('There is no user with this id. ')
        flash("Invalid token. Please try again.", "danger")
        return redirect(url_for('login'))
    
    form = PasswordForm()
    if form.validate_on_submit():
        # Only one post method attempt
        expiration_date = jwt.decode(token, app.secret_key, algorithms=['HS256'])['exp']
        redis.setex(token, expiration_date, 1)

        password = form.password.data

        hashed_password, _ =  hash_password(password)
        
        #print('The user is', response.user_id)
        password = Password.query.filter_by(user_id=response.user_id)
        password.hashed_password = hashed_password
        db.session.commit()

        #print('After forgeting password, user\' password is:', response.hashed_password)
        flash('The password has been updated successfully.', "success")
        return redirect(url_for('login'))
    
    return render_template('forget-password.html', form=form, title='Forgot Password')


@app.route('/view/chat/<string:chat_id>')
@jwt_required
def chat(user, chat_id: str):
    if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
    #print('Got request to start a chat. ')
    # TODO check for existed chat or send "" as html
    chat_info = get_chat_info(chat_id, user.user_id)
    blocked = chat_info['blocked']
    ##print(chat_info)
    if not blocked:
        socketio.on_namespace(ChatSockets(f'/chat/{chat_id}', chat_id))
        # Making all messages of some author seen when another friend connects
        see_peers_messages(chat_id, user.user_id) 
    else:
        #print('Chat won\'t be loaded because users are blocked. ')
        pass

    print('Chat route has done everything. Chat is active.')
    return jsonify(render_template('chat.html', chat_info=chat_info))

@app.route('/chat/pagination', methods=['GET'])
@jwt_required
def paginate_messages(user):
    ##print(request.args, request.view_args)
    chat_id, page_number = request.args.get('chatId'), request.args.get('pageNumber')
    if not chat_id or page_number is None: return [], 400
    if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
    messages = get_chat_history(chat_id, user, int(page_number))
    return jsonify(messages), 200


@app.route('/view/contacts', methods=['GET', 'POST'])
@jwt_required
def contacts(user):
    #print('Viewing contacts.')


    if request.method == 'POST':
        ##print('Post method in contacs.', request.data.decode('utf-8'))
        data = json.loads(request.data.decode('utf-8'))
        form =  ContactForm(MultiDict(data))
    else:
        form = ContactForm()
        # If post then there are will be errors send or submitting with changing chats. 
        # Thus I need to get chats when get method or when chats are changed.
        chats = get_chats(user.user_id)
        
    ##print('Contacts request:', request.headers, request.args, request.form, request)

    # Form validation checks both: csrf token and post request
    if form.validate_on_submit():
        #print('Contacts form validated on submit')
        #print('Form data from the contact is:', form.email.data, form.first_name.data)
        
        friend = form.validate_user() # is User typ
        #print('the friend with this email is:', friend)
        if not friend:
            return jsonify({'error': 'The person with this email address is not registered in Messenger yet.'}), 400
        elif BlockedUsers.are_blocked(user.user_id, friend.user_id):
            return jsonify({'error': 'The user has blocked you.'}), 400
        elif is_chat_exist('contact', user.user_id, friend.user_id): # check if there is a chat between them already
            return jsonify({'error': 'The chat already exists.'}), 400
            

        handle_create_chat('contact', [user, friend], 
                           {'first_name': form.first_name, 'last_name': form.last_name})
        chats = get_chats(friend.user_id)
        

        # Returning to the request from js. Any error which should be flashed will \
        # be delivered this way.
        return jsonify({'chats': chats}), 201
    else:
        # Like only first error
        for _, errors in form.errors.items():
            return jsonify({'error': errors[0]}), 400
        
    ##print('The chats are:', chats)
    #print('Sending contacts view html...')
    avatar_url = get_random_avatar()
    avatar = get_mongo_data_avatar(avatar_url, large=False)
    return jsonify(render_template('contacts.html', chats=chats, form=form, avatar=avatar))

@app.route('/view/home', methods=['GET', 'POST'])
@jwt_required
def view_home(user):
    #print('Viewing home.')
    if request.method == 'POST':
        formData = {
            **request.form,
            'image': request.files['image']
        }
        #print(formData)
        add_form =  NewGroupForm(MultiDict(formData))
    else:
        add_form = NewGroupForm()
        chats = get_chats(user.user_id, 'group')
        
    ##print('Contacts request:', request.headers, request.args, request.form, request)

    if add_form.validate_on_submit():
        #print('Home form validated on submit')
        #print('Form data from the contact is:', add_form.image.data, add_form.name.data)
            
        name = add_form.name.data
        image = add_form.image.data

        handle_create_chat('-', [user], 
                           {'name': name, 'image': image})
        chats = get_chats(user.user_id, 'group')
        
        return jsonify({'chats': chats}), 201
    else:
        # Like only first error
        for _, errors in add_form.errors.items():
            return jsonify({'error': errors[0]}), 400
        
    ##print('The chats are:', chats)
    #print('Sending home view html...')
    avatar_url = get_random_avatar()
    avatar = get_mongo_data_avatar(avatar_url, large=False) # The only cons is that size is quite large, but that's ok cuz usage of this image is small
    add_form.image.data = avatar # Prepopulating form for image background
    return jsonify(render_template('view-home.html', chats=chats, form=ReportBugForm(), add_form=add_form))

@app.route('/view/settings', methods=['GET'])
@jwt_required
def view_settings(user):
    #print('Viewing settings.')
    user_info = {
        'name': user.first_name + ' ' + user.last_name,
        'email': user.email,
        'avatar': get_user_static_avatar_url(user)
    }
    return jsonify(render_template('settings.html', user_info=user_info))

@app.route('/view/profile', methods=['GET', 'POST'])
@jwt_required
def edit_profile(user):
    #print('Viewing profile editing.')

    if request.method == 'POST':
        data = {
            **request.form,
            'avatar': request.files['avatar']
        }
        ##print(data)
        form =  EditProfileForm(MultiDict(data))
    else:
        form = EditProfileForm()

    if form.validate_on_submit():
        #print(
        #    'Edit profile form validated on submit. Form data:', 
        #    form.first_name.data, form.last_name.data, form.avatar.data, form.bio.data
        #)

        avatar = form.avatar.data
        if avatar is not None:
            previous_avatar = user.avatar
            delete_avatar_by_id(previous_avatar)
            processed_avatar = process_upload_image(avatar)
            user.avatar = processed_avatar
            #print('The avatar is', processed_avatar)

        # TODO should this be optimazed?
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.bio = form.bio.data
        db.session.commit()
        
        return "", 201
    else:
        for field, errors in form.errors.items():
            # error = errors[0].replace("field", field) -- maybe, disagn the text somehow
            return jsonify({'error': errors[0]}), 400

    user_info = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'avatar': get_user_static_avatar_url(user),
        'bio': user.bio
    }

    form.bio.data = user_info['bio']
    #form.avatar.data = user_info['avatar']

    return jsonify(render_template('edit-profile.html', user_info=user_info, form=form)), 200

@app.route('/view/chat_profile/<string:chat_id>')
@jwt_required
def view_chat_profile(user, chat_id):
    if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
    #print('Viewing profile chat.')
    # TODO: get friends info
    #print(chat_id)

    user_info = get_chat_data(chat_id, user.user_id, large=True)

    return jsonify(render_template('chat-profile.html', user_info=user_info))

@app.route('/view/edit_chat/<string:chat_id>', methods=['GET', 'POST'])
@jwt_required
def view_edit_chat(user, chat_id):
    if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
    #print('Viewing chat editing.')
    # Not changing friend's avatar yet...

    if request.method == 'POST':
        formData = {
            **request.form,
            'avatar': request.files['avatar']
        }
        #print(formData)
        # Must use MultiDict
        form =  EditProfileForm(MultiDict(formData))
    else:
        form = EditProfileForm()

    if form.validate_on_submit():
        #print(
        #    'Edit chat form validated on submit. Form data:', 
        #    form.first_name.data, form.last_name.data, form.avatar.data,
        #)

        data = {
            'name': [form.first_name.data, form.last_name.data],
            'avatar': form.avatar.data 
        }

        change_chat_data(chat_id, user.user_id, data)
        
        return "", 201
    else:
        for _, errors in form.errors.items():
            return jsonify({'error': errors[0]}), 400

    info = get_chat_data(chat_id, user.user_id)
    form.avatar.data = info['avatar']
    form.first_name.data = info['first_name']
    form.last_name.data = info['last_name']
    #print(info)

    return jsonify(render_template('edit-chat.html', form=form)), 200

@app.route('/view/add-members/<string:chat_id>', methods=['GET', 'POST'])
@jwt_required
def view_add_members(user, chat_id):
    if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
    #print('Viewing add members.')
    if request.method == 'POST':
        data = request.get_json()
        #print('POST METHOD WITH MEMBERS', data, chat_id)
        add_members(data, chat_id)
        return jsonify({'message': 'Members added.'}), 201
        
    members = get_members(chat_id, user.user_id)
    return jsonify(render_template('add-members.html', members=members))



# MESSAGE FUNCTIONS

@app.route('/message-functions', methods=['POST', 'DELETE'])
@jwt_required
def manage_messages(user):
    #print(request.args)
    if request.method == 'DELETE':
        chat_id, message_id = request.args.get('chat_id'), request.args.get('message_id')
        if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
        if not chat_id or not message_id: return "", 400
        #print('Deleting message.')
        
        delete_message(chat_id, message_id)
        return jsonify({'message': 'Message deleted.'}), 202
    
    if request.method == 'POST':
        chat_id = request.form.get('chat_id')
        if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
        #print('Got the request to add forwards.')
        status = handle_forwarding(user, **request.form)
        if not status: return jsonify({'error': "Something went wrong..."}), 400
        return "", 201 

@app.route('/chat-functions', methods=['GET', 'DELETE'])
@jwt_required
def manage_chats(user):
    chat_id = request.args.get('chat_id')
    if not chat_id: return "", 400
    if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))

    if request.method == 'DELETE':
        #print('Deleting chat.')
        delete_chat(chat_id)
        return jsonify({'message': 'Chat deleted.'}), 202
    
    if request.method == 'GET':
        #print('Request to block a user.')
        block_user(chat_id, user.user_id)
        return jsonify({'message': 'Chat deleted.'}), 200   
    
@app.route('/seeing-messages', methods=['POST'])
@jwt_required
def seeing_messages(user):
    #print('Request to see messages.')
    data = request.get_json()
    chat_id = data.get('chat_id')
    message_time = data.get('message_time')
    if not chat_id or not message_time: return "", 400
    if not is_member(chat_id, user.user_id): return redirect(url_for('view_home'))
    unseen_count = see_unseen_messages(chat_id, user.user_id, message_time)
    return jsonify({'count': unseen_count}), 200



# TODO must be restricted from users
@app.route('/search/<string:path>', methods=['POST'])
@jwt_required
def searching_query(user, path):
    query = request.get_json()
    #print('Resorses to search are:', path, query)
    # If query is "" everything will be returned.
    results = search(query, path, user.user_id)
    return jsonify({'chats': results})

@app.route('/report-bug', methods=['POST'])
@jwt_required
def report_bug(user):
    #print('Get request to validate the reporting bug form.')
    form =  ReportBugForm(MultiDict({**request.form}))

    if form.validate_on_submit():
        # To do something with bug. Maybe, to store in a database.

        return jsonify({'message': 'Report is successful. Thanks!'}), 200

    else:
        for field, errors in form.errors.items():
            error = errors[0].replace('Field', field.capitalize() + ' field')
            return jsonify({'error': error}), 400

    



@app.route('/', defaults={'path': ''})
@app.route('/home')
@app.route('/<path:path>')
@jwt_required
def home(user, path):
    #print(path, 'Rerouting with flask is activated.')
    return render_template('index.html')
