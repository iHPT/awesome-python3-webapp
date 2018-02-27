#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Default configurations.
'''

__author__ = 'hpt'

configs = {
    'debug': True,
    'database': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'db': 'test_db'
    },
    'session': {
        'secret': 'Awesome'
    }
}
