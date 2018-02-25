#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coroweb import get
import asyncio

@get('/')
async def index(request):
    print('test_view.py--/')
    return b'<h1>Awesome</h1>'

@get('/hello')
async def hello(request):
    print('test_view.py--/hello')
    return '<h1>hello!</h1>'

@get('/world')
async def world(request):
    print('test_view.py--/world')
    return 'world!'


