#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' url handlers '


from coroweb import get, post
import asyncio, time

from models import User, Blog

# 同一时间创建，会出现id一致，主键重复错误
tom = User(email='57937554@qq.com', passwd='232434', admin=True, name='Tom')
lily = User(id='00154235346346aljfdlsjfldsjfld', email='32434354@qq.com', passwd='565231', name='Lily')

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

@get('/blogs')
async def hello(request):
    print('test_view.py--/blogs')
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

@get('/api/users')
async def api_get_users():
    print('test_view.py--/api/users')
    users = await User.findAll()
    for user in users:
        user.passwd = '123456'
    return dict(users=users)

