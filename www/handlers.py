#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' url handlers '


import asyncio, time, re, logging, json, hashlib, base64

from aiohttp import web

import markdown2

from coroweb import get, post

from models import User, Blog, next_id
from apis import APIError, APIValueError
from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY = 'configs.session.secret'

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    print('user2cookie......')
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    print('cookie2user......', cookie_str)
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        print('cookie2user----', user)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1.')
            return None
        user.passwd = '******'
        return user # 将user返回到auth_factory
    except Exception as e:
        logging.exception(e)
        return None

# # 同一时间创建，会出现id一致，主键重复错误
# tom = User(email='57937554@qq.com', passwd='232434', admin=True, name='Tom')
# lily = User(id='00154235346346aljfdlsjfldsjfld', email='32434354@qq.com', passwd='565231', name='Lily')

@get('/users')
async def index(request):
    print('test_view.py--/users')
    # await User.saveItem(tom)
    # await User.saveItem(lily)
    users = await User.findAll()
    # for user in users:
    #     print('user----', user)
    return {
        '__template__': 'test.html',
        'users': users
    }

# @get('/')
# async def index(request):
#     print('test_view.py--/')
#     return b'<h1>Awesome</h1>'

@get('/')
async def hello(request):
    print('test_view.py--/')
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
        Blog(id='3', name='Learn Python', summary=summary, created_at=time.time() - 64800)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }

# @get('/api/users')
# async def api_get_users():
#     print('test_view.py--/api/users')
#     users = await User.findAll()
#     for user in users:
#         user.passwd = '123456'
#     return dict(users=users)

####################################################################

@get('/register')
def register():
    print('/register-----register......')
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    print('/signin-----signin......')
    return {
        '__template__': 'signin.html'
    }

@post('/api/authenticate')
async def authenticate(*, email, passwd):
    print('/api/authenticate-----authenticate......')
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findAll('email=?', [email]) # (where, args)->('email=?', [email])
    print(users)
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd: 将(user.id+传入的真实passwd)进行sha1加密，与数据库中user.passwd进行比对
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    print(passwd, sha1.hexdigest())
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    print('r=====', r)
    return r

@get('/signout')
def signout(request):
    print('/signout-----signout......')
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=86400, httponly=True)
    logging.info('user signed out.')
    return r

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$') # hao123@qq.www.ten.com
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    print('/api/users-----api_register_user......')
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('rigister:failed', 'email', 'Email is already in use.')
    uid = next_id()
    # 保存到数据库的user信息passwd进行shar1加密
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    print(user)
    print(user.passwd, hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest())
    await User.saveItem(user) # 将注册用户保存到数据库
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******' # 将密码变更，数据传输更安全
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8') # json.dumps序列化一个对象为字符串，另有sort_keys,indent参数来优化字符串格式；json.dump将一个对象序列化存入文件
    return r


