#!/usr/bin/env python
# -*- coding: utf-8 -*-


# orm TEST
from orm import Model, StringField, IntegerField, FloatField, create_pool, select, execute
import asyncio

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
    print('\n')
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
    loop.run_until_complete(test_findAll(loop))
    loop.run_until_complete(test_insert(loop, tom))
    loop.run_until_complete(test_findAll(loop))
    loop.run_until_complete(test_removeItem(loop, tom))
    loop.run_until_complete(test_remove(loop, 3))
    loop.run_until_complete(test_findAll(loop))
    tom = User(id=3, name='tom')
    loop.run_until_complete(test_insert(loop, tom))
    loop.run_until_complete(test_find(loop, 3))
    loop.run_until_complete(test_update(loop, 3, name='Mike'))
    loop.run_until_complete(test_findAll(loop))
    loop.close()


#以下为测试
#loop = asyncio.get_event_loop()
#loop.run_until_complete(create_pool(host='127.0.0.1', port=3306, user='root', password='123456',db='test1_db', loop=loop))
#rs = loop.run_until_complete(select('select * from Persons', None))
##获取到了数据库返回的数据
#print("Result:%s" % rs)

