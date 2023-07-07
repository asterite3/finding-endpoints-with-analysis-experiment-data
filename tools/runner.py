#!/usr/bin/env python3

import sys
import os
import json
import asyncio
import subprocess
import yaml
from pathlib import Path
import time
import signal
import datetime

DIR = Path(__file__).resolve().parent
CONFIG_PATH = DIR / 'stands.yml'
PROXY_PATH = str(DIR.parent / 'recordproxy')
CRAWLERS_PATH = DIR.parent / 'crawlers'
RESULTS_DIR = DIR / 'results'
PROXY_BIND_HOST = '100.72.55.11'
PROXY_PORT = 8000

HTCAP_PATH = 'crawlers/htcap'

TIMEOUT_MINUTES = 6 * 60
#TIMEOUT_MINUTES = 10
TIMEOUT = 60 * TIMEOUT_MINUTES

TEE_BUF_SIZE = 4096

# Crawljax
# HTcap
# Arachni
# W3af
# wget
# Enemy of the state https://github.com/adamdoupe/enemy-of-the-state

with open(CONFIG_PATH, encoding='utf8') as config_file:
    config = yaml.safe_load(config_file)

def log(*args):
    print(datetime.datetime.now(), *args, file=sys.stderr)

async def tee(in_stream, out1, out2):
    try:
        out1_writer = getattr(out1, 'buffer', out1)
        out2_writer = getattr(out2, 'buffer', out2)
        while True:
            buf = await in_stream.read(TEE_BUF_SIZE)
            if len(buf) == 0:
                break
            
            out1_writer.write(buf)
            out2_writer.write(buf)
    finally:
        out2.close()

class BaseCrawler:
    def __init__(self, target_name, target_url):
        self.p = None
        self.target_url = target_url
        self.results_dir = os.path.join(RESULTS_DIR, self.name(), target_name)
        self.stderr_writer = None
        self.stdout_writer = None
        os.makedirs(self.results_dir, exist_ok=True)

    @classmethod
    def name(cls):
        return cls.__name__.lower()

    async def start_process(self, *args, **kwargs):
        self.p = await asyncio.create_subprocess_exec(
            *args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self.create_output_writers()


    def create_output_writers(self):
        stdout_log = open(self.results_dir + "/out.log", "wb")
        stderr_log = open(self.results_dir + "/err.log", "wb")

        self.stdout_writer = asyncio.create_task(tee(self.p.stdout, sys.stdout, stdout_log))
        self.stderr_writer = asyncio.create_task(tee(self.p.stderr, sys.stderr, stderr_log))


    async def start(self):
        raise NotImplementedError()

    async def send_stop_signal_to_crawler(self):
        self.p.send_signal(signal.SIGINT) # SIGINT by default

    async def stop(self):
        if self.p.returncode is not None:
            return
        await self.send_stop_signal_to_crawler()
        try:
            await asyncio.wait_for(self.p.wait(), 3)
            return
        except asyncio.TimeoutError:
            log(f"crawler {self.name()} did not exit after SIGINT + 2 sec, try SIGTERM")
            self.p.terminate()
            try:
                await asyncio.wait_for(self.p.wait(), 3)
            except asyncio.TimeoutError:
                log(f"crawler {self.name()} did not exit after SIGTERM and SIGINT, kill")
                self.p.kill()
                await self.p.wait()

    async def wait(self):
        await self.stdout_writer
        await self.stderr_writer
        return await self.p.wait()

    def get_returncode(self):
        return self.p.returncode


class Crawljax(BaseCrawler):
    async def start(self):
        crawljax_path = CRAWLERS_PATH / 'crawljax/crawljax-cli-5.2.3'
        crawljax_jar = './crawljax-cli-5.2.3.jar'
        
        await self.start_process(
            'java', '-jar', crawljax_jar, '-b', 'CHROME_HEADLESS', '-t',
            str(TIMEOUT_MINUTES), self.target_url, self.results_dir + '/output',
            cwd=str(crawljax_path),
        )

class Htcap(BaseCrawler):
    HTCAP_PAGE_TIMEOUT = None

    async def start(self):
        htap_path = HTCAP_PATH
        htap_main = 'htcap.py'

        args = ['python3.6', htap_main, 'crawl', '-q', '-v']

        if self.HTCAP_PAGE_TIMEOUT is not None:
            args += ['-t', str(self.HTCAP_PAGE_TIMEOUT)]
        
        await self.start_process(
            *args, self.target_url, self.results_dir + '/output.db',
            cwd=htap_path
        )

    async def send_stop_signal_to_crawler(self):
        self.p.send_signal(signal.SIGINT)
        await asyncio.sleep(0.5)
        self.p.send_signal(signal.SIGINT)

class Wget(BaseCrawler):
    async def start(self):
        downloads_dir = os.path.join(self.results_dir, 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        await self.start_process(
            'wget', '-nv', '-r', self.target_url,
            cwd=str(downloads_dir)
        )

class Arachni(BaseCrawler):
    async def start(self):
        timeout_str = str(datetime.timedelta(seconds=TIMEOUT)).split('.')[0]
        arachni_path = CRAWLERS_PATH / 'arachni-1.6.1.3-0.6.1.1'
        
        await self.start_process(
            './bin/arachni', '--timeout', timeout_str, '--daemon-friendly',
             '--report-save-path', self.results_dir + '/report.afr',
             '--checks', 'inexiste*eeeeentabcd', self.target_url,
            cwd=str(arachni_path)
        )

    async def send_stop_signal_to_crawler(self):
        self.p.send_signal(signal.SIGINT)
        await asyncio.sleep(2)

class W3af(BaseCrawler):
    async def start(self):
        w3af_path = CRAWLERS_PATH / 'w3af'
        #w3af_profile_template = CRAWLERS_PATH / 'w3af_full_audit_template.pw3af'

        w3af_profile_template = CRAWLERS_PATH / 'w3af_spider_template.pw3af'

        with open(w3af_profile_template, encoding='utf8') as w3af_template_file:
            template = w3af_template_file.read()
        profile = template.replace('{{TARGET_URL}}', self.target_url)
        profile_path = self.results_dir + '/profile.pw3af'
        with open(profile_path, 'w', encoding='utf8') as profile_file:
            profile_file.write(profile)

        await self.start_process(
            'env/bin/python', 'w3af_console', '-P', profile_path,
            cwd=str(w3af_path)
        )

class EnemyOfTheState(BaseCrawler):
    @classmethod
    def name(cls):
        return 'enemy-of-the-state'

    async def start(self):
        output_dir = self.results_dir + '/output'
        os.makedirs(output_dir, exist_ok=True)

        await self.start_process(
            'docker', 'run', '--net', 'host', '--rm', '-v', output_dir + ':/output',
            'enemy-of-the-state',
            'jython', 'crawler2.py', '-F', '-d', '/output/requests',
            self.target_url
        )


async def wait_for_port(host, port):
    while True:
        try:
            _, writer = await asyncio.open_connection(host, port)
            break
        except OSError as err:
            await asyncio.sleep(0.2)
            continue
    writer.close()
    await writer.wait_closed()


async def start_proxy(out_file, stand_name):
    p = await asyncio.create_subprocess_exec(
        './recordproxy', '-c', str(CONFIG_PATH), '-o', out_file, '-p', str(PROXY_PORT), '-s', stand_name,
        cwd=str(PROXY_PATH)
    )
    await wait_for_port(PROXY_BIND_HOST, PROXY_PORT)
    return p

def make_target_url(target_name, target):
    target_addr = target_name
    dns_suffix = config.get('dns_suffix')
    if dns_suffix:
        target_addr = target_addr + '.' + dns_suffix
    path = target.get('path', '/')
    return f'http://{target_addr}{path}'

async def run_crawler_on_target(crawler_class, target_name, target):
    target_url = make_target_url(target_name, target)
    log('Run crawler', crawler_class.name(), 'on', target_name, target_url)
    t = time.time()
    crawler = crawler_class(target_name, target_url)
    proxy_process = await start_proxy(os.path.join(crawler.results_dir, 'requests.ndjson'), target_name)
    await crawler.start()

    try:
        await asyncio.wait_for(crawler.wait(), TIMEOUT + 3)
    except asyncio.TimeoutError:
        log('TIMEOUT: crawler', crawler_class.name(), 'timed out on', target_name, target_url, 'will stop it')
        if crawler.get_returncode() is None:
            await crawler.stop()
    proxy_process.terminate()
    await proxy_process.wait()
    log(
        'Done running crawler', crawler_class.name(), 'on', target_name, target_url,
        'it took', str(datetime.timedelta(seconds=(time.time() - t)))
    )

async def run_crawler(crawler_class):
    for target_name, target in config['stands'].items():
        await run_crawler_on_target(crawler_class, target_name, target)

async def run(crawler_set):
    crawlers = [Htcap, Crawljax, Wget, Arachni, W3af, EnemyOfTheState]

    if crawler_set:
        crawlers = [c for c in crawlers if c.name() in crawler_set]
        print("Loaded crawler set")
    print(f"Will run {len(crawlers)} crawlers: {str([c.name() for c in crawlers])}")
    for crawler_class in crawlers:
        await run_crawler(crawler_class)

if __name__ == '__main__':
    crawler_set = []
    crawler_set_path = DIR / 'crawler-set.json'
    if os.path.exists(crawler_set_path):
        with open(crawler_set_path) as crawler_set_file:
            crawler_set = json.load(crawler_set_file)
    asyncio.run(run(crawler_set))