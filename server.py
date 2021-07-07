import os
import logging
from datetime import datetime
import signal
import argparse

import asyncio
from aiohttp import web
import aiofiles


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


async def handle_404_page(request):
    async with aiofiles.open('page_404.html', 'r') as page_file:
        content = await page_file.read()
    return web.Response(text=content, content_type='text/html')


async def archiving(request):
    target_folder = os.path.join(os.getenv('root_folder'),
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

    try:
        while True:
            data = await proc.stdout.read(1024 * 5)
            if not data:
                break

            try:
                await response.write(data)
                logging.info('Sending archive chunk ...')
                await asyncio.sleep(float(os.getenv('delay')))
            except asyncio.CancelledError:
                proc.send_signal(signal.SIGKILL)
                logging.warning('Download was interrupted')
                break
    except SystemExit:
        proc.send_signal(signal.SIGKILL)
        _ = proc.communicate()
    return response


async def uptime_handler(request):
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'

    await response.prepare(request)

    while True:
        message_text = datetime.now().strftime('%d-%m-%Y %H:%M:%S<br>')
        await response.write(message_text.encode('UTF-8'))

        await asyncio.sleep(float(os.getenv('delay')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Проект микросервиса для загрузки фотографий')
    parser.add_argument('root_folder', help='Корневая папка с фотографиями')
    parser.add_argument('delay', help='Задержка сервера')
    parser.add_argument('--log', help='Включение журнала логирования')

    args = parser.parse_args()
    if args.log == 'ON':
        logging.basicConfig(level=logging.DEBUG)

    os.environ['root_folder'] = args.root_folder
    os.environ['delay'] = args.delay

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{hash_value}/', archiving),
        web.get('/uptime', uptime_handler)
    ])
    web.run_app(app)
