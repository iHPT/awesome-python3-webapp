#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio, logging
import aiomysql

# 设置调试级别level,此处为logging.INFO,不设置logging.info()没有任何作用等同于pass
logging.basicConfig(level=logging.INFO)

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

#创建数据库连接池,可以方便的从连接池中获取数据库连接
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        # 这个必须设置,否则,从数据库获取到的结果是乱码的
        charset=kw.get('charset', 'utf8'),
        # 是否自动提交事务,在增删改数据库数据时,如果为True,不需要再commit来提交事务了
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 50),
        minsize=kw.get('minsize', 1),
        loop=loop
    )

async def select(sql, args, size=None):
    print('select sql----------------------')
    log(sql, args)
    
    global __pool
    
    async with __pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            #调用游标的execute()方法来执行sql语句,execute()接收两个参数,第一个为sql语句可以包含占位符,第二个为占位符对应的值,使用该形式可以避免直接使用字符串拼接出来的sql的注入攻击
            #sql语句的占位符为?,mysql里为%s,做替换
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
    logging.info('rows returned: %s' % len(rs))
    # # 如果不关闭__pool，就会报异常：Exception ignored in: <bound method Connection.__del__ of <aiomysql.connection.Connection objec>>
    # __pool.close() # close()is not a coroutine, If you want to wait for actual closing of acquired connection please call wait_closed() after close().
    # await __pool.wait_closed()
    return rs

async def execute(sql, args, autocommit=True):
    print('execute sql----------------------')
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin() # 手动开始事务
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit() # 手动提交事务
        except BaseException as e:
            if not autocommit:
                await conn.rollback() # 出现提交事务异常时恢复原始数据
            raise e
    # # 如果不关闭__pool，就会报异常：Exception ignored in: <bound method Connection.__del__ of <aiomysql.connection.Connection objec>>
    # __pool.close() # close()is not a coroutine, If you want to wait for actual closing of acquired connection please call wait_closed() after close().
    # await __pool.wait_closed()
            return affected # 返回被执行的数据记录条数

def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
        
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='VARCHAR(100)'):
        super(StringField, self).__init__(name, ddl, primary_key, default)

class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict() 		# key-value对
        fields = [] 					# 保存主键外的字段
        primaryKey = None 		# 用来标记唯一的主键
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise BaseException('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise BaseException('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields)) # 给字段添加反引号``
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        attrs['__fields__'] = fields
        # 以下四种方法保存了默认了增删改查操作,其中添加的反引号``,是为了避免与sql关键字冲突的,否则sql语句会执行出错
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        # insert into table (key1, key2...) values(?, ?...), ?后续用参数替代
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values(%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        # update table set key1=?, key2=?,..., where primaryKey=?
        attrs['__update__'] = 'update `%s` set ? where `%s`=?' % (tableName, primaryKey) # set参数使用传入值设置
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super().__init__(**kw) # 古老写法super(Model, self).__init__(**kw)
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value
    
    def getValue(self, key):
        #调用getattr获取一个未存在的属性,也会走__getattr__方法,但是因为指定了默认返回的值,__getattr__里面的错误永远不会抛出
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value
    
    # find
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        'find objects by where clause.'
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args=[]
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]
    
    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        'find number by select and where.'
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']
    
    @classmethod
    async def find(cls, pk):
        'find object primary key.'
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])
    
    # insert
    @classmethod
    async def saveItem(cls, item):
        args = list(map(item.getValueOrDefault, item.__fields__))
        args.append(item.getValueOrDefault(item.__primary_key__))
        rows = await execute(cls.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)
    
    # update
    @classmethod
    async def update(cls, pk, **kw):
        #sql = 'update `%s` set %s where `%s`=?' % (cls.__table__, ', '.join(map(lambda item: '`%s`="%s"' % (item[0], item[1]), kw.items())), cls.__primary_key__) # `%s`="%s" value突出为字符串表示
        # 'update `%s` set ? where `%s`=?' 将第一个问号用kw参数替代
        sql = cls.__update__.replace('?', ', '.join(map(lambda item: '`%s`="%s"' % (item[0], item[1]), kw.items())), 1)
        rows = await execute(sql, pk)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)
    
    # remove
    @classmethod
    async def remove(cls, pk):
        #args = list(map(self.getValueOrDefault, self.__fields__))
        rows = await execute(cls.__delete__, pk)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)

    @classmethod
    async def removeItem(cls, item):
        #print('+++++++++++++++++', item.__primary_key__)
        rows = await execute(cls.__delete__, item.getValue(item.__primary_key__))
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)

'''
####################################################################
# 测试部分
async def get_pool(loop):
    return await create_pool(host='127.0.0.1', port=3306, user='root', password='123456', db='test_db', loop=loop)

class User(Model):
    __table__ = 'users'
    
    id = IntegerField(primary_key=True)
    name = StringField()
#				LastName = StringField()
#				City = StringField()

# 查询测试
async def test_findAll(loop):
    print('\n')
    await get_pool(loop)
    rs = await User.findAll() # 所有操作都是异步执行，否则异常
    for i in range(len(rs)):
        print(rs[i])
    print('test_findAll----all has been found.')

async def test_find(loop, pk):
    print('\n')
    await get_pool(loop)
    rs = await User.find(pk)
    print('test_find----table[%d]: %s' % (pk, rs))

# 增加测试
async def test_insert(loop, item):
    print('\n')
    await get_pool(loop)
    await User.saveItem(item) # vivien.save()实际并不会写入数据，所有的操作都需异步执行
    print('test_insert item at %d' % item.id)
#update(cls, pk, **kw):
# 更新测试
async def test_update(loop, pk, **kw):
    await get_pool(loop)
    await User.update(pk, **kw)
    print('test_update----table[%d]' % pk)

# 删除测试
async def test_remove(loop, pk):
    print('\n')
    await get_pool(loop)
    await User.remove(pk)
    print('test_remove----table[id=%d] removed.' % pk)

async def test_removeItem(loop, item):
    print('\n')
    await get_pool(loop)
    await User.removeItem(item)
    print('test_remove----table[id=%d] removed.' % item.id)

if __name__ == '__main__':
    tom = User(id=11, name='tom')
    loop = asyncio.get_event_loop() # 获取消息循环对象
    loop.run_until_complete(test_insert(loop, tom))
    loop.run_until_complete(test_findAll(loop))
    loop.run_until_complete(test_removeItem(loop, tom))
    loop.run_until_complete(test_remove(loop, 5))
    loop.run_until_complete(test_find(loop, 3))
    loop.run_until_complete(test_update(loop, 3, id=6, name='Mike'))
    loop.run_until_complete(test_findAll(loop))
    loop.close()


#以下为测试
#loop = asyncio.get_event_loop()
#loop.run_until_complete(create_pool(host='127.0.0.1', port=3306, user='root', password='123456',db='test1_db', loop=loop))
#rs = loop.run_until_complete(select('select * from Persons', None))
##获取到了数据库返回的数据
#print("Result:%s" % rs)
'''
