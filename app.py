import logging

from aiohttp import web
from json import dumps
from sys import stdout

import nshandler as ns


routes = web.RouteTableDef()


@routes.get('/api')
async def request_news_all(request):
    news_all = dumps(await ns.get_news_all(), indent=4)
    return web.Response(text=news_all)
    #return web.json_response(await get_news_all())


@routes.get('/api/news/{id}')
async def request_news(request):
    try:
        news_one = dumps(await ns.get_news_one(request.match_info['id']), indent=4)
        return web.Response(text=news_one)
        #return web.json_response(await get_news_one(request.match_info['id']))
    except ValueError:
        return web.HTTPNotFound()


@routes.post('/api/news')
async def add_news(request):
    await ns.create_news(await request.json())
    return web.Response(status=200)


@routes.delete('/api/news/{id}')
async def del_news(request):
    try:
        await ns.change_state(request.match_info['id'])
        return web.Response(status=200)
    except ValueError:
        return web.HTTPNotFound()


# Logging
logging.basicConfig(level=logging.DEBUG,
                    stream=stdout,
                    format='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
                    datefmt="%d/%b/%Y %H:%M:%S")
logging.getLogger('aiohttp.access')
logging.getLogger('aiohttp.server')
logging.getLogger('aiohttp.web')

# Run application
app = web.Application()
app.add_routes(routes)
web.run_app(app)
