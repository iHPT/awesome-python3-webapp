#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Models for user, blog, coment.
'''

__author__ = 'hpt'

import time, uuid
from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'
    
    id = StringField(primary_key=True, default=next_id, ddl='VARCHAR(50)')
    email = StringField(ddl='VARCHAR(50)')
    passwd = StringField(ddl='VARCHAR(50)')
    admin = BooleanField()
    name = StringField(ddl='VARCHAR(50)')
    image = StringField(ddl='VARCHAR(500)')
    created_at = FloatField(default=time.time)

class Blog(Model):
    __table__ = 'blogs'
    
    id = StringField(primary_key=True, default=next_id, ddl='VARCHAR(50)')
    user_id = StringField(ddl='VARCHAR(50)')
    user_name = StringField(ddl='VARCHAR(50)')
    user_image = StringField(ddl='VARCHAR(500)')
    name = StringField(ddl='VARCHAR(50)')
    summary = StringField(ddl='VARCHAR(200)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):
    id = StringField(primary_key=True, default=next_id, ddl='VARCHAR(50)')
    blog_id = StringField(ddl='VARCHAR(50)')
    user_id = StringField(ddl='VARCHAR(50)')
    user_name = StringField(ddl='VARCHAR(50)')
    user_image = StringField(ddl='VARCHAR(500)')
    content = TextField()
    created_at = FloatField(default=time.time)

