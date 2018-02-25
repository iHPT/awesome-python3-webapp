#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'hpt'

import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web
from apis import APIError

# def get(path):
#     '''
#     Define decorator @get('/path')
#     '''
#     def decorator(func):
#         @functools.wraps(func)
#         def wrapper(*args, **kw):
#             return func(*args, **kw)
#         wrapper.__method__ = 'GET'
#         wrapper.__route__ = path
#         return wrapper
#     return decorator

# def post(path):
#     '''
#     Define decorator @post(/path)
#     '''
#     def decorator(func):
#         @functools.wraps(func)
#         def wrapper(*args, **kw):
#             return func(*args, **kw)
#         wrapper.__method__ = 'POST'
#         wrapper.__route__ = path
#         return wrapper
#     return decorator

# 建立视图函数装饰器，用来存储、附带URL信息
def handler_decorator(path, *, method):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = method
        wrapper.__route__ = path
        return wrapper
    return decorator
# 偏函数。GET POST 方法的路由装饰器
get = functools.partial(handler_decorator, method='GET')
post = functools.partial(handler_decorator, method='POST')


# 使用inspect模块，检查视图函数的参数
# inspect.Parameter.kind 类型：
# POSITIONAL_ONLY          位置参数
# KEYWORD_ONLY             命名关键词参数
# VAR_POSITIONAL           可选参数 *args
# VAR_KEYWORD              关键词参数 **kw
# POSITIONAL_OR_KEYWORD    位置或必选参数

# 获取无默认值的命名关键词参数
def get_required_kw_args(fn):
    args = []
    '''
    def foo(a, b = 10, *c, d,**kw): pass
    sig = inspect.signature(foo) ==> <Signature (a, b=10, *c, d, **kw)>
    sig.parameters ==>  mappingproxy(OrderedDict([('a', <Parameter "a">), ...])) 
    sig.parameters.items() ==> odict_items([('a', <Parameter "a">), ...)]) 
    sig.parameters.values() ==>  odict_values([<Parameter "a">, ...]) 
    sig.parameters.keys() ==>  odict_keys(['a', 'b', 'c', 'd', 'kw']) 
    '''
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

# 获取命名关键词参数
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

# 判断是否有命名关键词参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

# 判断是否有关键词参数
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 判断是否含有名叫'request'的参数，且位置在最后
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (
            param.kind != inspect.Parameter.VAR_POSITIONAL and
            param.kind != inspect.Parameter.KEYWORD_ONLY and
            param.kind != inspect.Parameter.VAR_KEYWORD):
            # 若判断为True，表明param只能是位置参数。且该参数位于request之后，故不满足条件，报错。
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found


'''
RequestHandler需要处理以下问题：
1、确定HTTP请求的方法（’POST’or’GET’）（用request.method获取）
2、根据HTTP请求的content_type字段，选用不同解析方法获取参数。（用request.content_type获取）
3、将获取的参数经处理，使其完全符合视图函数接收的参数形式
4、调用视图函数
'''
# 定义RequestHandler从视图函数中分析其需要接受的参数，从web.Request中获取必要的参数
# 调用视图函数，然后把结果转换为web.Response对象，符合aiohttp框架要求
class RequestHandler(object):
    def __init__(self, app, fn):
        print('RequestHandler--__init__....')
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)
    
    # 1.定义kw，用于保存参数
    # 2.判断视图函数是否存在关键词参数，如果存在根据POST或者GET方法将request请求内容保存到kw
    # 3.如果kw为空（说明request无请求内容），则将match_info列表里的资源映射给kw；若不为空，把命名关键词参数内容给kw
    # 4.完善_has_request_arg和_required_kw_args属性
    async def __call__(self, request):
        print('RequestHandler--__call__....')
        print('request =', request, '; method =', request.method, '; content_type =', request.content_type)
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            print('@@@@@@@@@@@@@@@@@@@@')
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json() # 仅解析body字段的json数据
                    if not isinstance(params, dict): # request.json()返回dict对象
                        return web.HTTPBadRequest(text='JSON body must be object.')
                    kw = params
                # form表单请求的编码形式
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post() # 返回post的内容中解析后的数据。dict-like对象。
                    kw = dict(**params) # 组成dict，统一kw格式
                else:
                    return web.HTTPBadRequest(text='Unsurpported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string # 返回URL查询语句，?后的键值。string形式。
                if qs:
                    kw = dict()
                    '''
                    解析url中?后面的键值对的内容
                    qs = 'first=f,s&second=s'
                    parse.parse_qs(qs, True).items()
                    >>> dict([('first', ['f,s']), ('second', ['s'])])
                    '''
                    for k, v in parse.parse_qs(qs, True).items(): # 返回查询变量和值的映射，dict对象。True表示不忽略空格。
                        kw[k] = v[0]
        
        if kw is None: # 若request中无参数
            print('#################')
            # request.match_info返回dict对象。可变路由中的可变字段{variable}为参数名，传入request请求的path为值
            # 若存在可变路由：/a/{name}/c，可匹配path为：/a/jack/c的request
            # 则reqwuest.match_info返回{name = jack}
            kw = dict(**request.match_info)
        else: # request有参数
            print('======================')
            if not self._has_var_kw_arg and self._named_kw_args: # 若视图函数只有命名关键词参数没有关键词参数
                # remove all unnamed kw:
                copy = dict()
                # 只保留命名关键词参数
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy # kw中只存在命名关键词参数
            # 将request.match_info中的参数传入kw
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Dumplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg: # 视图函数存在request参数
            print('---------------------')
            kw['request'] = request
        if self._required_kw_args: # 视图函数存在无默认值的命名关键词参数
            print('&&&&&&&&&&&&&&&&&&&&&&&')
            for name in self._required_kw_args:
                if not name in kw: # 若未传入必须参数值，报错。
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)
        # 至此，kw为视图函数fn真正能调用的参数
        # request请求中的参数，终于传递给了视图函数
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


'''
add_route函数功能：
1、验证视图函数是否拥有method和path参数
2、将视图函数转变为协程
'''
# 编写一个add_route函数，用来注册一个视图函数
def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    # 判断URL处理函数是否协程并且是生成器
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn) # 将fn转变成协程
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    # 在app中注册经RequestHandler类封装的视图函数，至此，RequestHandler的__call__直接处理视图函数
    app.router.add_route(method, path, RequestHandler(app, fn))

# 导入模块，批量注册视图函数
def add_routes(app, module_name):
    n = module_name.rfind('.') # 从右侧检索，返回索引。若无，返回-1。
    #print('module_name =', module_name, '; n =', n)
    # 导入整个模块
    if n == -1:
        # __import__ 作用同import语句，但__import__是一个函数，并且只接收字符串作为参数
        # __import__('os',globals(),locals(),['path','pip'], 0) ,等价于from os import path, pip
        mod = __import__(module_name, globals(), locals(), [], 0)
        #print('mod =', mod) # mod = <module 'test_view' from '/.../www/test_view.py'>
    else:
        name = module_name[n+1:]
        # 只获取最终导入的模块，为后续调用dir()
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name], 0), name)
        #print('name =', name, '; mod =', mod)
    for attr in dir(mod): # dir()迭代出mod模块中所有的类，实例及函数等对象,str形式
        #print('attr', attr)
        if attr.startswith('_'):
            continue # 忽略'_'开头的对象，即内置属性__builtins__, __doc__, __file__等，直接继续for循环
        fn = getattr(mod, attr)
        # 确保是函数
        if callable(fn):
            # 确保视图函数存在method和path
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                #print('call add_route...')
                add_route(app, fn) # 注册


# 添加静态文件，如image，css，javascript等
def add_static(app):
    # 拼接static文件目录
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static') # /.../awesome-python3-webapp/www/static/
    # path = os.path.join(os.path.abspath('.'), 'static')
    
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))
