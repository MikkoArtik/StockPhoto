import os
import asyncio
from datetime import datetime
from aiohttp import web

import aiofiles
import logging


ROOT_FOLDER = '/home/michael/Документы/Education/AsyncPython/StockPhoto/' \
              'async-download-service/test_photos'


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


async def handle_404_page(request):
    async with aiofiles.open('page_404.html', 'r') as page_file:
        content = await page_file.read()
    return web.Response(text=content, content_type='text/html')


async def archivate(request):
    target_folder = os.path.join(ROOT_FOLDER,
                                 request.match_info['hash_value'])
    if not os.path.exists(target_folder):
        return await handle_404_page(request)

    response = web.StreamResponse()

    header_val = 'attachment; filename="archive.zip"'
    response.headers['Content-Disposition'] = header_val

    await response.prepare(request)

    command = ['zip', '-r', '-j', '-', target_folder]
    proc = await asyncio.subprocess.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE)

    logging.info('Start sending...')

    while True:
        data = await proc.stdout.read(1024 * 5)
        if not data:
            break

        await response.write(data)
        logging.info('Sending archive chunk ...')
    return response


async def uptime_handler(request):
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'

    await response.prepare(request)

    while True:
        message_text = datetime.now().strftime('%d-%m-%Y %H:%M:%S<br>')
        await response.write(message_text.encode('UTF-8'))

        await asyncio.sleep(0.1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{hash_value}/', archivate),
        web.get('/uptime', uptime_handler)
    ])
    web.run_app(app)
