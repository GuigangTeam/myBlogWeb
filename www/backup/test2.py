import orm,asyncio
from models import User,Blog,Comment
loop=asyncio.get_event_loop()
@asyncio.coroutine
def test():
	yield from orm.create_pool(loop,user='www-data',password='www-data',db='awesome')
	u=User(name='Test',email='test@example.com',passwd='123456',admin=False,image='about:blank',created_at="123")
	yield from u.save()
loop.run_until_complete(test())