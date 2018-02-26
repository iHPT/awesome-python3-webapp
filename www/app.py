#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'hpt'

'''
async web application
'''

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import orm
from coroweb import add_routes, add_static


'''
初始化jinja2需要以下几步：
1、对Environment类的参数options进行配置。
2、使用jinja提供的模板加载器加载模板文件，程序中选用FileSystemLoader加载器直接从模板文件夹加载模板。
3、有了加载器和options参数，传递给Environment类，添加过滤器，完成初始化。
'''
def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    # class Environment(**options)
    # 配置options参数
    options = dict(
        # 自动转义xml/html的特殊字符
        autoescape = kw.get('autoescape', True),
        # 代码块的开始、结束标志
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        # 变量的开始、结束标志
        variable_start_string = kw.get('variable_start_string', '{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        # 自动加载修改后的模板文件
        auto_reload = kw.get('auto_reload', True)
    )
    # 获取模板文件夹路径
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates') # /.../awesome-python3-webapp/www/templates/
    logging.info('set jinja2 templates path: %s' % path)
    # Environment类是jinja2的核心类，用来保存配置、全局对象以及模板文件的路径
    # FileSystemLoader类加载path路径中的模板文件
    env = Environment(loader=FileSystemLoader(path), **options)
    # 过滤器集合
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            # filters是Environment类的属性：过滤器字典
            env.filters[name] = f
     # 所有的一切是为了给app添加__templating__字段
    # 前面将jinja2的环境配置都赋值给env了，这里再把env存入app的dict中，这样app就知道要到哪儿去找模板，怎么解析模板。
    app['__templating__'] = env # app是一个dict-like对象


# 编写一个过滤器：
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

'''
编写middleware
middlerware是符合WSGI定义的中间件。位于服务端和客户端之间对数据进行拦截处理的一个桥梁。可以看过服务器端的数据，经middleware一层层封装，最终传递给客户端。
参考资料：WSGI
web框架正是由一层层middleware的封装，才具备各种完善的功能。所以我们需要编写middlerware对视图函数返回的数据进行处理。如：构造Response对象。
其实middleware和装饰器类似，它会对视图函数返回的数据进行处理，达成想要的目的。

编写一个简单的用于打印日志的middleware：
# 编写用于输出日志的middleware
'''
# 编写用于输出日志的middleware
# handler是视图函数
async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        # await asyncio.sleep(1)
        return (await handler(request))
    return logger

async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data

# 处理视图函数返回值，制作response的middleware  
# 请求对象request的处理工序：  
#     logger_factory => response_factory => RequestHandler().__call__ => handler  
# 响应对象response的处理工序：  
# 1、由视图函数处理request后返回数据  
# 2、@get@post装饰器在返回对象上附加'__method__'和'__route__'属性，使其附带URL信息  
# 3、response_factory对处理后的对象，经过一系列类型判断，构造出真正的web.Response对象
async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request) # 调用RequestHandler.__call__，对参数进行处理
        if isinstance(r, web.StreamResponse): # StreamResponse是所有Response对象的父类
            print('response "StreamResponse"')
            return r # 无需构造，直接返回
        if isinstance(r, bytes):
            print('response "bytes"')
            resp = web.Response(body=r) # 继承自StreamResponse，接受body参数，构造HTTP响应内容
            # Response的content_type属性
            resp.content_type = 'application/octet-stream'
            print('resp =', resp)
            return resp
        if isinstance(r, str):
            print('response "str"')
            if r.startswith('redirect:'): # 若返回重定向字符串
                return web.HTTPFound(r[9:]) # 重定向至目标URL
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8' # utf-8编码的text格式
            print('resp =', resp)
            return resp
        # r为dict对象时
        if isinstance(r, dict):
            print('response "dict"')
            # 在后续构造视图函数返回值时，会加入__template__值，用以选择渲染的模板
            template = r.get('__template__')
            if template is None: # 不带模板信息，返回json对象
                # ensure_ascii：默认True，仅能输出ascii格式数据。故设置为False。  
                # default：r对象会先被传入default中的函数进行处理，然后才被序列化为json对象  
                # __dict__：以dict形式返回对象属性和值的映射
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                print('resp =', resp)
                return resp
            else: # 带模板信息，渲染模板
                # app['__templating__']获取已初始化的Environment对象，调用get_template()方法返回Template对象  
                # 调用Template对象的render()方法，传入r渲染模板，返回unicode格式字符串，将其用utf-8编码
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8' # utf-8编码的html格式
                print('resp =', resp)
                return resp
        # 返回响应码
        if isinstance(r, int) and r >= 100 and r < 600:
            print('response "int"')
            return web.Response(status=r)
        # 返回了一组响应代码和原因，如：(200, 'OK'), (404, 'Not Found')
        if isinstance(r, tuple) and len(r) == 2:
            print('response "tuple"')
            t, m =r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(status=r, text=str(m))
        # default:
        print('response "default"')
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        print('resp =', resp)
        return resp
    return response

async def init(loop):
    await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password='123456', db='awesome')
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    # add_routes导入模块名，调用add_route，内部app.router.add_route创建RequestHandler实例
    add_routes(app, 'handlers') # module_name为独立模块名，或带.的模块名的子模块
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000) # 当向服务器发出请求时，会进行中间层middlewares函数调用，并调用RequestHandler实例__call__函数，进行处理
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()





'''
def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
'''

