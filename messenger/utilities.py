import hashlib
import os
from flask_mailman import EmailMessage
from messenger import group_chats, contact_chats, redis, db, app
from messenger.models import User, BlockedUsers
import uuid
import datetime
from flask import url_for
from PIL import Image
import pathlib
from random import random


MESSAGE_READ_ICON_URL = '/static/resources/message-read.png'
MESSAGE_UNREAD_ICON_URL = '/static/resources/message-unread.png'
IMAGE_LARGE_X = 420
IMAGE_LARGE_Y = 420
IMAGE_SMALL_X = 58
IMAGE_SMALL_Y = 58
OUTPUT_IMAGE_SIZES = [(IMAGE_LARGE_X, IMAGE_LARGE_Y), (IMAGE_SMALL_X, IMAGE_SMALL_Y)]




# COMMON


def generate_id(prefix=""):
    id = uuid.uuid4()
    id = prefix + str(id.int)[:10]
    return id

# TODO I probably should implement encaplsulation: state or template pattern
def get_chat_type(chat_id):
    # "-" is for groups
    # "" for contacts
    return 'contact' if chat_id[0] != '-' else 'group'

def get_random_avatar():
    # Returned format as for db
    return f"avatar_{int(random() * 6) + 1}.png"

def get_my_image_ext(avatar_id: str):
    name, ext = os.path.splitext(avatar_id)
    return name, ext

def get_user_static_avatar_url(user, large=True):
    name, ext = get_my_image_ext(user.avatar)
    if large:
        return f"/static/avatars/{name}_{IMAGE_LARGE_X}x{IMAGE_LARGE_Y}{ext}"
    else:
        return f"/static/avatars/{name}_{IMAGE_SMALL_X}x{IMAGE_SMALL_Y}{ext}"

def delete_avatar_by_id(avatar_id):
    if avatar_id is None: return # There wasn't any prior avatar 
    # Input avatar is from db (with its format)

    default_prefix = 'avatar_'
    if avatar_id.startswith(default_prefix):
        return 
    
    name, ext = get_my_image_ext(avatar_id)
    
    for x, y in OUTPUT_IMAGE_SIZES:
        file_path = os.path.join(app.static_folder, f'avatars/{name}_{x}x{y}{ext}')
        if os.path.exists(file_path): 
            os.remove(file_path)
            #print(f"File '{file_path}' deleted successfully.")
        else: 
            #print(f"File '{file_path}' not found.")
            pass

def delete_past_avatar(chat_id, user_id=None):
    chat_type = get_chat_type(chat_id)

    if chat_type == 'contact': path = f'contacts.{user_id}.avatar'
    else: path = 'group_data.image'

    query = {'chat_id': chat_id, path: {'$exists': True}}
    project = {'_id': 0, path: 1}

    if chat_type == 'contact':
        chat = contact_chats.find_one(query, project)
        #print(chat)
        avatar_id = chat['contacts'][f'{user_id}']['avatar'] 
    else:
        chat = group_chats.find_one(query, project)
        avatar_id = chat['group_data']['image']

    delete_avatar_by_id(avatar_id)
    

def is_member(chat_id, user_id):
    # The goal of this function is to make sure the request is processed from a valid user - the one who  
    # registered in the chat. The opposite is to try to manage chats of other people.
    # Maybe, check for memebership/blocking is needed.
    # Also check if chat exists at all
    chat_type = get_chat_type(chat_id)
    if chat_type == 'contact':
        chat = contact_chats.find_one({'chat_id': chat_id, f'contacts.{user_id}': {'$exists': True}})
    else:
        chat = group_chats.find_one({'chat_id': chat_id, 'users': user_id})

    if not chat:
        return False

    return True

def get_user_fullname(user):
    fullname = user.first_name + ' ' + user.last_name
    if len(fullname) > 16: fullname = fullname[:13] + '...'
    return fullname

def get_mongo_data_avatar(avatar_id, large=False):
    name, ext = get_my_image_ext(avatar_id)
    #print('MONGO LEARGE AVATAR', large)
    if large:
        #print(9)
        avatar_url = f'{name}_{IMAGE_LARGE_X}x{IMAGE_LARGE_Y}{ext}'
    else: 
        avatar_url = f'{name}_{IMAGE_SMALL_X}x{IMAGE_SMALL_Y}{ext}'
    return url_for('static', filename=f'avatars/{avatar_url}')

def get_message_by_id(message_id, cur_filter, chat_type):
    query = {'_id': 0, 'messages': {
        '$elemMatch': {'id': message_id}
    }}

    if chat_type == 'contact':
        item = contact_chats.find_one(cur_filter, query)
    else:
        item = group_chats.find_one(cur_filter, query)

    #print(item, query, cur_filter)
    if not item: return
    message = item['messages'][0]
    return message


# HTML GENERATING

# Generates html for one message
def generate_message_html(chat_type, message, user):
    # Note that group chats have mine as an attribute.
    forwarded_by = message.get('forwarded')
    if not forwarded_by: forward_html = ""
    else:
        user = User.query.get(forwarded_by)
        fullname = get_user_fullname(user)
        avatar_url = get_user_static_avatar_url(user)
        forward_html = f"""<div class="forwarded-header">
            <i class="fa-solid fa-share"></i>
            <img src={avatar_url} alt="avatar" />
            <span>{fullname}</span>
        </div>"""


    time = datetime.datetime.strftime(message['time'], "%H:%M")
    person_upper_name = ""
    person_left_container = ""
    read_icon = ""

    if message['mine']:
        message_icon = MESSAGE_UNREAD_ICON_URL if message['unseen'] else MESSAGE_READ_ICON_URL
        read_icon = f" <img src={message_icon} alt='check' />"
    elif chat_type == "group":
        # Person title name plus avatar
        is_next_message_mine = message.get('is_next_message_mine', True)
        is_prev_message_mine = message.get('is_prev_message_mine', True)
        person_left_avatar = ""
        if not is_next_message_mine or not is_prev_message_mine:
            author = User.query.filter_by(user_id=message['author_id']).first()
        
            ##print('SDFLSDJFLSDKFSDFSKDF', is_next_message_mine, is_prev_message_mine)
            if not is_next_message_mine:
                # We need to have avatar right in this message
                avatar = get_user_static_avatar_url(author)
                person_left_avatar = f"""<img class="little-avatar" src={avatar} alt="avatar" />"""
            
            if not is_prev_message_mine:    
                # Adding an upper title for message because prev is not mine
                fullname = get_user_fullname(author)
                person_upper_name = f"""<div class='person-upper-name'>{fullname}</div>"""
        
        # Do container this way because messages in contacts doesn't have left container
        person_left_container = f'<span class="little-avatar-container">{person_left_avatar}</span>'

    # Don't change first and last spaces because it impacts client rendering
    # by having #text elements in the container
    html = f"""<div class="{message['mine']}" id="{message['id']}" data-message-time="{message['time']}">
    {person_left_container}
    <div class="message">
        {person_upper_name}
        {forward_html}
        <div class="text">
            {'<div class="forwarded-border"></div>' if forward_html else ""}
            <div>
                <span class="message-text">{message['text']}</span>
                <span class="info"><span class="time">{time}</span>{read_icon}</span>
            </div>
        </div>
    </div></div>"""
    return html



# NEW MESSAGE

def add_message_to_collection(chat_id, message, user, forwarded="", id=None):
    chat_type = get_chat_type(chat_id)
    user_id = user.user_id
    if not id: id = generate_id()
    time = datetime.datetime.now()
    #print('The time of message is', time)
    # I store the author id only inside the database. It's secure
    # TODO I probably don't need author id with groups and only iwth contact_chats
    msg = {
        'id': id,
        'author': user_id,
        'forwarded': forwarded, # Id of the initial author of the forwarded message
        'message': message,
        'time': time
    }
    
    #current_time = datetime.datetime.now()
    ##print(current_time.strftime("%d/%m/%Y, %H:%M:%S"))

    cur_filter = {'chat_id': chat_id}
    access_query = {'_id': 0, 'unseen_messages.author_id': 1}

    if chat_type == 'contact':
        chat = contact_chats.find_one(cur_filter, access_query)
    else:
        chat = group_chats.find_one(cur_filter, access_query)

    prev_author = chat['unseen_messages']['author_id']
    if prev_author == user_id:
        # Adding one new message
        query = {
            '$push': {'messages': msg}, '$set': {
                'last_modified': datetime.datetime.now(), 
                f'unseen_messages.{id}': 1 # The message is unseen
            }
        }
    else:
        # Changing with author
        query = {
            '$push': {'messages': msg}, '$set': {
                'last_modified': datetime.datetime.now(), 
                'unseen_messages': {
                    'author_id': user_id, # Should be null before setting this OR The current author (if they talk online) will be overwritten 
                                                # Thus the messages become seen when friend send his message after you sent your own message in real time
                                                # But you will not see that the friend saw your messages because I don't update the fronted display 
                    f'id': 1 # The message is unseen
                }
            }
        }

    query['$set']['unseen_messages_by_user'] = {}
    query['$set']['unseen_messages_by_user'][f'{user_id}'] = time
    

    if chat_type == 'contact':
        chat = contact_chats.find_one(cur_filter)
        if len(chat['contacts']) == 1: # Means the friend isn't aware that the user have added him as a friend
            add_friends_info(chat_id, chat, user)
        contact_chats.update_one(cur_filter, query)
    else:
        group_chats.update_one(cur_filter, query)


def determine_next_prev(prev_author, nextt_author, cur_author):
    ##print('AHUTORS', prev_author, nextt_author, cur_author)
    # If next mine, do nothing. If prev mine, do nothing.
    # If it is your message, you need nothing.
    # If it contacts, you need nothing.
    is_next_message_mine = is_prev_message_mine = True
    if not prev_author == cur_author: # prev is mine
        is_prev_message_mine = False
    if not nextt_author == cur_author: # next is mine
        is_next_message_mine = False
    return is_next_message_mine, is_prev_message_mine


def handle_message(chat_id, message, mine, user, id=None):
    chat_type = get_chat_type(chat_id)
    if id is None: id = generate_id("")

    is_next_message_mine = is_prev_message_mine = True

    if chat_type != 'group':
        # Eliminating avatar swaping in mine and contacts messages
        is_prev_message_mine = False

    if mine: 
        # I can do this because the only time a user adds a message to collection is when he sends directly.
        add_message_to_collection(chat_id, message, user, id=id)
    elif chat_type == 'group':
        # There is no next message, always swap or add.
        is_next_message_mine = False

        data = group_chats.find_one({'chat_id': chat_id}, 
            {
                '_id': 0, # There is no other way of escluding these things.
                'group_data': 0,
                'unseen_messages': 0,
                'users': 0,
                'last_modified': 0,
                'messages': {'$slice': -2} # -2 because last message is the current message
            }
        )
        if data and len(data['messages']) > 0:
            last_message = data['messages'][0]
            is_prev_message_mine = last_message['author'] == user.user_id

    ms_info = {
        'forwarded': None, 
        'text': message,
        'id': id,
        'mine': mine, 
        'unseen': True, # By default is unseen. This is the most painful part but there is no not complex way to fix this in real time chatting
        'time': datetime.datetime.now(),
        'is_next_message_mine': is_next_message_mine,
        'is_prev_message_mine': is_prev_message_mine,
        'author_id': user.user_id # this is always the author of message regradless if it mine or not
    }
    html_message = generate_message_html(chat_type, ms_info, user)

    # Sending next message mine from here in order to eliminate elaborating with contacts/groups 
    return html_message, is_prev_message_mine, id # for deleting avatar from previous message


# Generates last n messages from the history (+ html for every of them) 
def get_chat_history(chat_id, user, page_number):
    user_id = user.user_id

    ''' Explaing different message styling:
    We get a message cluster of length limit n and we need to process it for 
    particular messages which will have title name at the top and avatar at left.
    In the cluster we have two edge cases: first message and last message. Thus
    we need two additional border messages to identify these on the edge.
    After we have some edge cases according to this which we need to handle.

    - We always process current and skip before first, after last ones.

    Edge cases:
    1) No nextt (nextt is the the oldest among messages later than current), len(messages) % n = 0
    2) No cur, only prev
    3) No prev (prev is the latest message among messages older than current), right starting
    4) No messages at all
    5) No nextt and no prev, only cur

    NOTE: MINE IS TOWARD THE AUTHOR OF MESSAGE, not current user
    '''

    n = 30 
    start = n * page_number
    #print('Paginating chat histroy, start', start)

    no_prev = True if start == 0 else False

    pipeline = [
        { '$match': {'chat_id': chat_id} },
        { '$unwind': '$messages'}, # create an arrya of documents = messages field. Every element is document now
        { '$sort': {'messages.time': -1}}, # sort every element of message (messages is collection of documents)
        { '$skip': max(0, start - 1)}, # before first
        { '$limit': n + 2 - no_prev}, # before first and after last
        { '$group': {'_id': '$_id', 'messages': {'$push': '$messages'}, # decode backwards into an array which is created automatically because of push 
                     'unseen_messages': { '$first': '$unseen_messages' }}}, 
        { '$project': { # returns only the fields you want
            '_id': False,
            'messages': True,
            'unseen_messages': True
        }}
    ]

    chat_type = get_chat_type(chat_id)
    if chat_type == 'contact':
        mongo_messages = list(contact_chats.aggregate(pipeline=pipeline))
    else:
        mongo_messages = list(group_chats.aggregate(pipeline=pipeline))

    # Fourth case. First condition for message paginating into a wall.
    if not mongo_messages or not mongo_messages[0].get('messages', []): return ""

    def get_ms_info(cur, unseen) -> dict:
        return {
            'forwarded': cur.get('forwarded'),
            'text': cur['message'],
            'id': cur['id'],
            'mine': 'mine' if user_id == cur['author'] else "",
            'unseen': unseen,
            'time': cur['time']
        }

    def add_mines(ms_info, prev_author, nextt_author, cur_author):
        is_next_message_mine, is_prev_message_mine = determine_next_prev(
            prev_author, nextt_author, cur_author)
        ms_info['is_next_message_mine'] = is_next_message_mine
        ms_info['is_prev_message_mine'] = is_prev_message_mine
        ms_info['author_id'] = cur_author
        return ms_info
    
    def handle_create_message(cur, unseen, prev_author, nextt_author) -> dict:
        ms_info = get_ms_info(
            cur, 
            unseen
        )

        if chat_type == 'group' and not ms_info['mine']:
            ms_info = add_mines(
                ms_info, prev_author, nextt_author, cur['author']
            )

        ##print(ms_info)

        return ms_info

    unseen_messages = mongo_messages[0].get('unseen_messages') # Shouldn't be None
    mongo_messages = mongo_messages[0].get('messages')
    ##print(mongo_messages) 

    # actual number of messages to process
    actual_length = len(mongo_messages)

    # Second case
    if actual_length - (not no_prev) == 0: return ""
    no_nextt = True if actual_length != n + 2 - no_prev else False
    #print('Second case passed.', actual_length, no_prev, no_nextt)

    # Fifth case
    # Third case
    if no_prev:
        mongo_messages = [{'author': None}] + mongo_messages
        actual_length += 1
    #print('Third case passed.')

    # First case
    if no_nextt:
        mongo_messages.append({'author': None})
        actual_length += 1
    #print('Fourth case passed.')
    ##print("Outcome messages: ", mongo_messages)

    prev = mongo_messages[-1] # prev
    cur = mongo_messages[-2] # the first message - current

    # TODO edge cases conditions - for one length of messages

    messages = []
    for i, nextt in enumerate(mongo_messages[:actual_length - 1 - no_nextt][::-1]): # n + 2 - 1 - one to exclude prev; actual length
        ##print(nextt, i)

        ms_info = handle_create_message(
            cur, 
            unseen_messages.get(cur['id']), # I don't check author id should be user's one or null. If null there aren't messages
            prev['author'],
            nextt['author']
        )

        messages.append(generate_message_html(chat_type, ms_info, user))

        prev = cur
        cur = nextt
    
    ##print('History messages:', messages)
    return "".join(messages)



# NEW MEMBERS 


def add_group_user(chat_id, user_id, delete=False):
    group_chats.update_one({'chat_id': chat_id}, {'$set': {f'users.{user_id}': 1}})


def add_friends_info(chat_id, chat, user):
    friend_id = chat['contacts'][f'{user.user_id}']['friend_id']
    user_info = { # Setting default user's (first friend) data
        'avatar': None,
        'name': user.first_name + ' ' + user.last_name,
        'friend_id': user.user_id
    }
    contact_chats.update_one(
        {'chat_id': chat_id}, {'$set': {f'contacts.{friend_id}': user_info}}
    )


# CREATING CHATS


def create_contact_chat(chat_id, users, data):
    # First user in users must be the user who created the chat!
    # I don't need to store user's data: it always can be accessed with user - I store friend's data
    
    user, friend = users
    friend_name = [data['first_name'].data, data['last_name'].data] # names are from flask wtform
    cur_time = datetime.datetime.now()
    user_id, friend_id = user.user_id, friend.user_id
    #print(data, friend_name, user, friend)
    
    chat_data = {
        'chat_id': chat_id,
        'contacts': { # User: friends_info
            f'{user_id}': { # This is custom data that every user could change
                'avatar': None, # If None then get default friend's avatar from db
                'name': friend_name,
                'friend_id': friend_id # Could be accessed and after deleted, but I won't delete for next functions and future scalability
            }
        }, 
        'last_modified': cur_time,
        'messages': [],
        'unseen_messages': {'author_id': None},
        'unseen_messages_by_user': {f'{user_id}': cur_time, f'{friend_id}': cur_time}
    }
    contact_chats.insert_one(chat_data)

def create_group_chat(chat_id, users, data):
    name, image = data['name'], data['image'] 
    ##print(name, image)
    cur_time = datetime.datetime.now()
    user_id = users[0].user_id # There is only one user on creation always.
    group_chats.insert_one({
        'chat_id': chat_id, 
        'group_data': {'name': name, 
                       'image': process_upload_image(data['image']) if image else get_random_avatar()
        },
        'users': [user_id], 
        'last_modified': cur_time,
        'messages':[], 
        'unseen_messages':{'author_id': None}, 
        'unseen_messages_by_user': {f'{user_id}': cur_time},
        'creator': user_id # Current user. Needed for editing the group.
    })

def handle_create_chat(chat_type, users, data):
    # I will use chat_id field for id of chat instead of _id field.
    # The reason is the efforts needed to convert uuid4 into bson.ObjectId()
    
    if chat_type == 'contact':
        chat_id = generate_id('')
        # Contact chat
        create_contact_chat(chat_id, users, data)
    else:
        chat_id = generate_id('-')
        # Group chat
        create_group_chat(chat_id, users, data)

    return chat_id



# GENERATING CHATS DATA & GETTING CHATS

def get_count_unseen_messages(messages: list, last_timestamp: datetime.datetime):
    # Performing binary search
    N = len(messages)
    start, end = 0, N - 1
    while start <= end:
        m = (end + start) >> 1 # // 2
        m_date = messages[m]['time']
        #print(m_date, start, end, m)
        if m_date <= last_timestamp:
            start = m + 1
        else:
            end = m - 1
    ##print(N, N - start, start, m, end, m_date, last_timestamp)
    return N - start # start starts from the message that is later than last_timestamp

def generate_data_for_chat(chat, user_id):
    chat_id = chat['chat_id']
    chat_type = get_chat_type(chat_id)
    last_message = chat['messages'][-1] if chat['messages'] else None
    if last_message is not None:
        message = last_message['message']

        if last_message['author'] == user_id:
            author_name = 'You'
        else:
            author = User.query.filter_by(user_id=last_message['author']).first()
            author_name = author.first_name + " " + author.last_name
        author_name += ': '
        
        n = len(author_name)
        if len(message) > 30 - n:
            message = message[:max(30 - n, 0)] + '...'
    else:
        message = "..."
        author_name = ""
    
    unit = {
        'chat_id': chat_id,
        'last_message': {
            'message': message,
            'author': author_name
        }
    }

    if chat_type == 'contact':
        friend_data = chat['contacts'][f'{user_id}']
        unit['image'] = get_friends_avatar(friend_data)
        unit['name'] = " ".join(friend_data['name'])
    else:
        group_data = chat['group_data']
        if not group_data['image']:
            unit['image'] = get_random_avatar()
        else:
            avatar_url = get_mongo_data_avatar(group_data['image'], large=False)
            unit['image'] = avatar_url
        unit['name'] = group_data['name']
    
    if len(unit['name']) > 28: 
        unit['name'] = unit['name'][:25] + '...'

    last_timestamp = chat['unseen_messages_by_user'][f'{user_id}']
    unseen_count = get_count_unseen_messages(chat['messages'], last_timestamp)
    #print('UNSEEN COUNT FOR PERSON', unseen_count)
    unit['unseen_messages_exist'] = unseen_count

    return unit
    


def get_chats(user_id, chat_type='contact'):
    chats = contact_chats.find({f'contacts.{user_id}': {"$exists": True}}).sort({'last_modified': -1})
    if chat_type == 'group':
        # NOTE: I can search inside array like that.
        chats = sorted(list(chats) + list(group_chats.find({'users': user_id})), key=lambda x: x['last_modified'], reverse=True)

    # Costly funtion but we need to sort form newest to oldest. 
    # I don't think there are 10000+ chats that one user has.
    # I think this is better than sorting only one of them by inherit mongo sort.
    #chats = sorted(chats, key=lambda x: x['last_modified'], reverse=True)

    data = []
    #print('Generating chats...')
    for chat in chats:
        data.append(generate_data_for_chat(chat, user_id))
    
    # HTML generating directly with jinja2
    #print(data)
    return data


def generate_members_data(users, include={}):
    members = []
    for user_id in users:
        user = User.query.filter_by(user_id=user_id).first()
        cur = {
            # There is always last name in db (not when updating friend's one)
            'name': user.first_name + " " + user.last_name,
            'image': get_user_static_avatar_url(user),
            'status': get_time_status(user),
        }
        if include.get('user_id'): cur['peer_id'] = user.user_id
        members.append(cur)
    return members

def get_groups_info(chat_id, user_id, include_members=False, large=False):
    chat = group_chats.find_one({'chat_id': chat_id}, {'_id': 0, 'users': 1, 'group_data': 1, 'chat_id': 1})
    group_data = chat['group_data']
    blocked = True if BlockedUsers.are_blocked(user_id, chat['chat_id']) else False
    members_length = len(chat['users'])
    avatar_url = get_mongo_data_avatar(group_data['image'], large=large)
    info = {
        'avatar': avatar_url,
        'title': group_data['name'],
        'members_or_status': '1 member' if members_length == 1 else f'{members_length} members',
        'blocked': blocked,
        'type': 'group'
    }
    if include_members:
        info['members'] = generate_members_data(chat['users'])
    return info

def get_contacts_info(chat_id, user_id):
    chat = contact_chats.find_one({'chat_id': chat_id}, {'_id': 0, 'contacts': 1})
    friend_data = chat['contacts'][f'{user_id}']
    friend_id = friend_data['friend_id']
    blocked = True if BlockedUsers.are_blocked(user_id, friend_id) else False
    info = {
        'avatar': get_friends_avatar(friend_data),
        'title': " ".join(friend_data['name']),
        'members_or_status': get_time_status(User.query.filter_by(user_id=friend_data['friend_id']).first()),
        'blocked': blocked,
        'type': 'contact'
    }
    return info

# Don't need to know user in group chat data
def get_chat_info(chat_id, user_id):
    chat_type = get_chat_type(chat_id)
    if chat_type == 'contact':
        return get_contacts_info(chat_id, user_id)
    elif chat_type == 'group':
        return get_groups_info(chat_id, user_id)

def get_members(chat_id, user_id):
    # Getting all contacts that doesn't belong to the current group
    # I don't know whta is more performant: getting all contacts and look up in set
    # or doing this:
    chat = group_chats.find_one({'chat_id': chat_id}, {'_id': 0, 'users': 1})
    users = chat['users']
    res = contact_chats.find({'$and': [
        {f'contacts.{user_id}': {"$exists": True}},
        {f'contacts.{user_id}.friend_id': {'$nin': users}}
    ]}, {'_id': 0, f'contacts.{user_id}.friend_id': 1})

    members_ids = []
    for item in res:
        #print(item)
        members_ids.append(item['contacts'][f'{user_id}']['friend_id'])
    return generate_members_data(members_ids, include={
        'user_id': True
    })


def add_members(members, chat_id):
    chat = group_chats.find_one({'chat_id': chat_id}, {'_id': 0, 'users': 1, 'unseen_messages_by_user': True})
    chat['users'] += members
    timestamps = chat['unseen_messages_by_user']
    for user_id in members:
        timestamps[f'{user_id}'] = datetime.datetime.now()
    
    group_chats.update_one({'chat_id': chat_id}, 
        {'$set': {
            'users': chat['users'],
            'unseen_messages_by_user': timestamps
    }})
    #print('Members added successfully')

# PASSWORDS



def hash_password(password: str, salt: str = None):
    if not salt: salt = os.urandom(15)
    result = hashlib.sha256(password.encode('utf-8') + salt).hexdigest()
    return [result, salt]




# EMAILS



def create_email_message(redirect_uri, comment):
    if comment == 'Modifying':
        return (f"""
        Continue with the link to change your password in Messenger. 
        <a style="color:black;" href={redirect_uri}>Change Password</a>
        """, 'Update Password Messenger')
    else:
        return (f"""
        Continue with the link to log into Messenger. 
        <a style="color:black;" href={redirect_uri}>Log Into.</a>
        """, 'Log Into Messenger')
    

def send_email_confirmation(email, redirect_uri, comment):
    #print('start sending confirmation email')
    try:
        html_body, subject = create_email_message(redirect_uri, comment)

        msg = EmailMessage(
            subject=subject,
            body=html_body,
            from_email='messenger_authentication@gmail.com',
            to=[email]
        )

        # We inlcude html exactly
        msg.content_subtype = 'html'
        msg.send()
        ##print('message is sent', msg, redirect_uri, email)
    except Exception as e:
        #print(e)
        return 
    
    #print('#printing message: successful sending')
    return "The email was successfully sent. "



# SEARCHING

def match_prefix(prefix, name):
    return name.lower().startswith(prefix.lower())


def search(query, chat_type, user_id):
    # Searching by the contacts chat where user is included and where the name of friend is in info
    chats = contact_chats.find({f'contacts.{user_id}': {"$exists": True}})
    if chat_type == 'group':
        chats = list(chats) + list(group_chats.find({'users': user_id}))

    chats = sorted(chats, key=lambda x: x['last_modified'], reverse=True)
        
    ##print('searching chats', chats)
    results = []
    for chat in chats:
        is_contact = chat.get('contacts')
        if not is_contact:
            name = chat['group_data']['name']
        else:
            name = " ".join(chat['contacts'][f'{user_id}']['name'])

        # Maybe, I could match the prefix doing database query.
        if match_prefix(query, name):
            results.append(
                generate_data_for_chat(chat, user_id)
            )
    
    #print('Results after searching are:', results)
    return results
    


# IMAGE

def process_upload_image(picture, quality=90):
    _, f_extension = get_my_image_ext(picture.filename)
    avatar_id = str(uuid.uuid4())
    static_folder_filename = f"static/avatars/{avatar_id}"
    current_dir_path = pathlib.Path(__file__).parent.resolve() # Slashes side doesn't matter
    for size_x, size_y in OUTPUT_IMAGE_SIZES:
        new_filename = os.path.join(current_dir_path, static_folder_filename + f'_{size_x}x{size_y}' + f_extension)
        img = Image.open(picture)
        img = img.resize((size_x, size_y), Image.Resampling.LANCZOS) # Resampling filter
        img.save(new_filename, quality=quality, optimaze=True)

    # Storing in db without size
    # I have only three extensions which have length of 3. can utilize it.
    return avatar_id + f_extension
    
        


# ONLINE / OFFLINE

def renew_online_user(user):
    user.last_seen = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    db.session.commit()

def calculate_date_diff(d1: str, d2: str):
    # day, month, year, hour, minute, second
    d1 = datetime.datetime.strptime(d1, "%Y-%m-%d %H:%M:%S") 
    d2 = datetime.datetime.strptime(d2, "%Y-%m-%d %H:%M:%S") 
    return abs(d1 - d2).seconds

def get_time_status(user):
    if not user: return 'Undefined'
    last_seen = user.last_seen
    #print(last_seen)
    current_time = str(datetime.datetime.now().replace(microsecond=0))
    time_dif = calculate_date_diff(current_time, last_seen)
    if time_dif < 120:
        return 'online'
    elif time_dif < 3600:
        return f"Last seen {time_dif // 60} minutes ago"
    elif time_dif < 24 * 3600:
        return f"Last seen {time_dif // 3600} hours ago"
    elif time_dif < 3 * 24 * 3600:
        return f"Last seen {time_dif // 3600 // 24} days ago"
    else:
        return f"Last seen {last_seen[:10]}"
    


# FRIEND INFO

def get_friends_avatar(friend_data, large=False):
    avatar = friend_data['avatar']
    if avatar == None:
        friend = User.query.get(friend_data['friend_id'])
        avatar = get_user_static_avatar_url(friend, large=large)
    else:
        
        avatar = get_mongo_data_avatar(avatar, large=large)
    return avatar

def get_chat_data(chat_id, user_id, large=False):
    chat_type = get_chat_type(chat_id)
    if chat_type == 'contact':
        chat = contact_chats.find_one({'chat_id': chat_id}, {'_id': 0, 'contacts': 1})
        friend_data = chat['contacts'][f'{user_id}']
        friend_id = friend_data['friend_id']
        email = User.query.get(friend_id).email
        info = {
            'avatar': get_friends_avatar(friend_data, large=large),
            'first_name': friend_data['name'][0],
            'last_name': friend_data['name'][1] or '',
            'title': " ".join(friend_data['name']),
            'members_or_status': get_time_status(User.query.filter_by(user_id=friend_id).first()),
            'email': email,
            'type': 'contact'
        }
    else:
        info = get_groups_info(chat_id, user_id, include_members=True, large=large)
        info['first_name'] = info['title']
        info['last_name'] = None
    return info

def change_chat_data(chat_id, user_id, data):
    ##print('SDFDFSDFSDFFD', data['avatar'])
    chat_type = get_chat_type(chat_id)
    cur_filter = {"chat_id": chat_id}

    if data['avatar']:
        # Send user id always, tho use it only for contacts.
        delete_past_avatar(chat_id, user_id)
        avatar = process_upload_image(data['avatar'])
    else:
        # If avatar is None, i let it be the same
        avatar = None

    if chat_type == 'contact':
        query = {f'contacts.{user_id}.name': data['name']}
        if avatar is not None:
            query[f'contacts.{user_id}.avatar'] = avatar

        contact_chats.update_one(cur_filter,
            {
                # Using multiple sets because don't want to lose friend_id field if set to contacts.user_id
                '$set': query
            }
        )
    else:
        query = {
            'group_data.name': data['name'][0]  # Only first name which is title in group chat
        }

        if avatar is not None:
            query['group_data.image'] = avatar

        group_chats.update_one(cur_filter,
            {
                # Using multiple sets because don't want to lose friend_id field if set to contacts.user_id
                '$set': query
            }
        )

    
    # Expensive to use for one function. May be optimized from js
    # return get_chat_data(chat_id, user_id)


# MANAGING MESSAGE FUNCTIONS

def delete_message(chat_id, message_id) -> None:
    chat_type = get_chat_type(chat_id)
    cur_filter = {"chat_id": chat_id}
    query = {
        '$pull': {'messages': {'id': message_id}}, # from messages
        '$unset': {f'unseen_messages.{message_id}': ""}
    }

    if chat_type == 'contact':
        contact_chats.update_one(cur_filter, query)
    else:
        group_chats.update_one(cur_filter, query)
    

# forwarded: chat_id, message_id || ""
# functions touched: generating html, generating data, UI design, db
def handle_forwarding(user, chat_id, message_id, forward_to):
    # Storing the data of forwarded message inside destination chat
    #print('SDFSDFSDF', chat_id, forward_to, message_id)

    chat_type = get_chat_type(chat_id)
    cur_filter = {'chat_id': chat_id}

    message = get_message_by_id(message_id=message_id, chat_type=chat_type, cur_filter=cur_filter)
    if not message: return
    ##print(message)

    text = message['message']
    initial_author = message['author']
    
    ##print(text, initial_author)

    add_message_to_collection(
        forward_to, # destination chat
        text, 
        user, 
        initial_author
    )

    return True # no errors

# I do think this is the best way instead of storing seen/unseen in every message because updating will be too hard
def see_peers_messages(chat_id, user_id):
    chat_type = get_chat_type(chat_id)
    cur_filter = {'chat_id': chat_id}

    if chat_type == 'contact':
        chat = contact_chats.find_one(cur_filter, {'_id': 0,'unseen_messages': 1})
    else:
        chat = group_chats.find_one(cur_filter, {'_id': 0,'unseen_messages': 1})
    author = chat['unseen_messages']['author_id']
    ##print(author)

    if author is not None and user_id != author:
        query = {
            '$set': {
            'unseen_messages': {
                'author_id': None
            }}
        }

        # Resetting unseen messages to no unseen messages (thus the author will not see that they are unseen)
        if chat_type == 'contact':
            contact_chats.update_one(cur_filter, query)
        else: 
            group_chats.update_one(cur_filter, query)

def see_unseen_messages(chat_id, user_id, message_time):
    chat_type = get_chat_type(chat_id)

    cur_filter = {'chat_id': chat_id}
    #print(message_time)
    if message_time == 'current':
        ''' If you want a message time by last timestamp of a user:
        - I think this approach with getting timestamp is better for scalability
        because you will probably want to set chat from the position of lastly read message
        instead of bottom. But I don't wanna do this for now.

        query = {'_id': 0, 'messages': 1, 'unseen_messages_by_user':1}
        if chat_type == 'contact':
            chat = contact_chats.find_one(cur_filter, query)
        else:
            chat = group_chats.find_one(cur_filter, query)
        message_time = str(chat['unseen_messages_by_user'][f'{user_id}'])'''

        # Using the fact that when chat is opened all messages are read automatically
        message_time = str(datetime.datetime.now())

    # Converts the date string to datetime object
    timestamp = datetime.datetime.strptime(message_time, "%Y-%m-%d %H:%M:%S.%f")
    #print(timestamp)
    #print('MESSAGE TIME', message_time, timestamp)

    query = {
        '$max': {f'unseen_messages_by_user.{user_id}': timestamp}
    }

    # Not checkin if timestamp is less because it's impossible
    if chat_type == 'contact':
        contact_chats.update_one(cur_filter, query)
        chat = contact_chats.find_one(cur_filter, {'_id': 0, 'messages': 1})
    else:
        group_chats.update_one(cur_filter, query)
        chat = group_chats.find_one(cur_filter, {'_id': 0, 'messages': 1})

    unseen_count = get_count_unseen_messages(chat['messages'], timestamp)
    #print('Unseen messages was seen by the user')
    return unseen_count

# MANAGING CHATS

def delete_chat(chat_id):
    chat_type = get_chat_type(chat_id)
    if chat_type == 'contact':
        contact_chats.delete_one({'chat_id': chat_id})
    else: 
        group_chats.delete_one({'chat_id': chat_id})

def block_user(chat_id, user_id):
    # Done only for contact chats...
    #print('Blocking the users', chat_id, user_id)
    chat = contact_chats.find_one({'chat_id': chat_id})
    friend_id = chat['contacts'][f'{user_id}']['friend_id']
    prev = BlockedUsers.query.filter_by(user_id=user_id, friend_id=friend_id).first()

    # Check by prev here because we add a blocked pair - not check
    if prev is None:
        item = BlockedUsers(user_id=user_id, friend_id=friend_id)
        db.session.add(item)
    else:
        #print('The pair of users is already blocked. Unblocking them', prev)
        db.session.delete(prev)
    db.session.commit()

def is_chat_exist(chat_type, user_id, friend_id):
    if chat_type == 'contact':
        chat = contact_chats.find_one({'$or': [
            {f'contacts.{user_id}.friend_id': friend_id},
            {f'contacts.{friend_id}.friend_id': user_id}
        ]})

        return chat is not None
