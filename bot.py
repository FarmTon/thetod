import os
import sys
import time
import json
import httpx
import random
import asyncio
import argparse
import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, unquote

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

class Tethertod:
    BASE_URL = "https://tap-tether.org"
    LOGIN_URL = f"{BASE_URL}/server/login"
    CLICK_URL_TEMPLATE = f"{BASE_URL}/server/clicks?clicks={{}}&lastClickTime={{}}"
    
    def __init__(self, query: str, click_min: int, click_max: int, interval: int):
        self.query = query
        self.marin_kitagawa = {key: value[0] for key, value in parse_qs(query).items()}
        user = json.loads(self.marin_kitagawa.get("user"))
        self.first_name = user.get("first_name")
        self.authorization = f"tma {query}"
        self.base_headers = self._get_base_headers()
        self.ses = httpx.AsyncClient(headers=self.base_headers, timeout=200)
        self.click_min = click_min
        self.click_max = click_max
        self.interval = interval

    def _get_base_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en,en-US;q=0.9",
            "Access-Control-Allow-Origin": "*",
            "Connection": "keep-alive",
            "Host": "tap-tether.org",
            "Referer": "https://tap-tether.org/?tgWebAppStartParam=ZJHQ8GY",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 10; Redmi 4A / 5A Build/QQ3A.200805.001; wv)"
                " AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.185"
                " Mobile Safari/537.36"
            ),
        }

    def log(self, msg: str) -> None:
        logging.info(f"[{self.first_name}] {msg}")

    async def http(self, url: str, data: Optional[Dict[str, Any]] = None) -> httpx.Response:
        headers = self.base_headers.copy()
        headers['Authorization'] = self.authorization
        while True:
            try:
                res = await self.ses.post(url, headers=headers, data=data) if data else await self.ses.get(url, headers=headers)
                with open("http.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f"{res.text}\n")
                return res
            except (httpx.HTTPError, httpx.ConnectError) as e:
                self.log(f"Connection error: {e}")
                await asyncio.sleep(1)
            except httpx.RemoteProtocolError as e:
                self.log(f"Server not sending response: {e}")
                await asyncio.sleep(1)

    async def start(self) -> bool:
        res = await self.http(self.LOGIN_URL)
        if res.status_code != 200:
            return False
        error = res.json().get("error")
        if error and "Expires data" in error:
            self.log("This account needs new query data!")
            return False
        data = res.json().get("userData")
        usdt = int(data.get("balance")) / 1000000
        usdc = int(data.get("balanceGold")) / 1000000
        re_click = int(data.get("remainingClicks"))
        self.log(f"Balance: {usdt} USDT, {usdc} USD Gold")
        
        while re_click >= 10:
            click = min(random.randint(self.click_min, self.click_max), re_click)
            click_url = self.CLICK_URL_TEMPLATE.format(click, round(time.time()))
            res = await self.http(click_url)
            if res.status_code != 200:
                return False
            self.log(f"Success sending tap: {click}")
            re_click = int(res.json().get("remainingClicks"))
            await countdown(self.interval)
        
        return True

async def countdown(t: int) -> None:
    for i in range(t, 0, -1):
        hours, remainder = divmod(i, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"Waiting {hours:02}:{minutes:02}:{seconds:02}", end="\r", flush=True)
        await asyncio.sleep(1)

async def main() -> None:
    with open("config.json") as config_file:
        config = json.load(config_file)
    
    click_min = config["click_range"]["min"]
    click_max = config["click_range"]["max"]
    interval = config["interval_click"]
    countdown_time = config["countdown"]
    
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--data", default="data.txt")
    args = arg_parser.parse_args()
    
    os.system("cls" if os.name == "nt" else "clear")
    print("""
    Auto Taptether Bot
    
    By: @AkasakaID
    """)
    
    with open(args.data) as data_file:
        datas = [line for line in data_file.read().splitlines() if line]
    
    print(f"Total accounts: {len(datas)}")
    while True:
        tasks = [Tethertod(query, click_min, click_max, interval).start() for query in datas]
        await asyncio.gather(*tasks)
        await countdown(countdown_time)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit()
