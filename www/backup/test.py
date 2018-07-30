import orm,asyncio
from models import User,Blog,Comment
def test():
	loop=asyncio.get_event_loop()
	yield from orm.create_pool(loop,user='www-data',password='www-data',db='awesome')
	u=User(name='Test',email='test@example.com',passwd='123456',image='about:blank')
	yield from u.save()
	loop.run_until_complete(init(loop))
	loop.run_forever()
for x in test():
	pass