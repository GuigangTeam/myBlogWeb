import asyncio,os,inspect,logging,functools
from urllib import parse
from aiohttp import web
from apis import APIError
def get(path):
	'''
	Define decorator @get('/path')
	'''
	logging.info("path:%s" % path)
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__='GET'
		wrapper.__route__=path
		return wrapper
	return decorator
def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__='POST'
		wrapper.__route__=path
		return wrapper
	return decorator
def get_required_kw_args(fn):
	args=[]
	params=inspect.signature(fn).parameters    # 获取函数fn的参数
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:  # KEYWORD_ONLY 命名关键字参数
			args.append(name)
	return tuple(args)
def get_named_kw_args(fn):
	args=[]
	params=inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)
def has_named_kw_args(fn):
	params=inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind==inspect.Parameter.KEYWORD_ONLY:
			return True
#VAR_KEYWORD **kwargs
def has_var_kw_arg(fn):
	params=inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind==inspect.Parameter.VAR_KEYWORD:
			return True
# VAR_POSITIONAL *args
def has_request_arg(fn):
	sig=inspect.signature(fn)
	params=sig.parameters
	found=False
	for name,param in params.items():
		if name=='request':
			found=True
			continue
		if found and (param.kind!=inspect.Parameter.VAR_POSITIONAL and param.kind!=inspect.Parameter.KEYWORD_ONLY and param.kind!=inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameters must be the last named parameters in function:%s%s' % (fn.__name__,str(sig)))
	return found		
class RequestHandler(object):
	def __init__(self,app,fn):
		self._app=app
		self._func=fn
		self._has_request_arg=has_request_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._has_var_kw_arg=has_var_kw_arg(fn)
		self._named_kw_args=get_named_kw_args(fn)
		self._required_kw_args=get_required_kw_args(fn)
	async def __call__(self,request):
		logging.info("coroweb.py 3")
		logging.info("self._app=%s" % self._app)
		logging.info("self._func=%s" % self._func)
		logging.info(request.method)
		logging.info(self._has_request_arg)
		logging.info(self._has_named_kw_args)
		logging.info(self._has_var_kw_arg)
		logging.info(self._named_kw_args)
		logging.info(self._required_kw_args)
		kw=None
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
			if request.method=='POST':
				if not request.content_type:
					return web.HTTPBadRequest('Missing Content-Type.')
				ct = request.content_type.lower()
				logging.info("ct %s" % ct)
				if ct.startswith('application/json'):
					params=await request.json()
					if not isinstance(params,dict):
						return web.HTTPBadRequest('JSON body must be object.')
					kw=params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart.form_data'):
					params=await request.post()
					kw=dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type:%s' % request.content_type)
			if request.method=='GET':
				qs=request.query_string
				if qs:
					kw=dict()
					for k,v in parse.parse_qs(qs,True).items():
						kw[k]=v[0]
		if kw is None:
			logging.info("coroweb.app request.match_info")
			kw=dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				logging.info("Get else")
				copy=dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name]=kw[name]
				kw=copy
			for k,v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args:%s' % k)
				kw[k]=v
		if self._has_request_arg:
			kw['request']=request
		if self._required_kw_args:
			for name in self._required_kw_args:
				logging.info("name=%s" % name)
				logging.info("kw=%s" % kw)
				if not name in kw:
					logging.info("not name in kw")
					return web.HTTPBadRequest('Missing argument: %s' % name)
		logging.info('call with args:%s' % str(kw))
		try:
			r=await self._func(**kw)
			return r
		except APIError as e:
			return dict(error=e.error,data=e.data,message=e.message)
def add_static(app):
	path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
	app.router.add_static('/static/',path)
	logging.info('add static %s=>%s' % ('/static/',path))
def add_route(app,fn):
	method=getattr(fn,'__method__',None)
	path=getattr(fn,'__route__',None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn=asyncio.coroutine(fn)
	logging.info('add route %s %s=>%s(%s)' % (method,path,fn.__name__,','.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method,path,RequestHandler(app,fn))
def add_routes(app,module_name):
	logging.info('Load add_routes')
	n=module_name.rfind('.')
	logging.info(n)
	if n==(-1):
		mod=__import__(module_name,globals(),locals())
	else:
		name=module_name[n+1:]
		mod=getattr(__import__(module_name[:n],globals(),locals(),[name]),name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn=getattr(mod,attr)
		if callable(fn):
			method=getattr(fn,'__method__',None)
			path=getattr(fn,'__route__',None)
			logging.info(fn)
			if method and path:
				add_route(app,fn)