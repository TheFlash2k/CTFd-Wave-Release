#!/usr/bin/env python3

import argparse
import json
from pprint import pprint
import os
from discord import Webhook
import aiohttp
from datetime import datetime
import pytz
import time
import asyncio


from utils.ctfd import CTFd_Handler
from utils.handler import RequestHandler, Mode
from utils.logger import logger, logging
from utils.utils import get_env

def get_notification_message(msg: str, challs: list, for_discord: bool = False):
    title = "New Wave Released"
    ln = "\n" if for_discord else "\n\n"
    msg = f"**{msg}**"
    msg += f"{ln}Following challenges have been released:{ln}"
    i = 1
    for chal in challs:
        name = chal['name'].replace("*", "").replace("#", "")
        from urllib.parse import quote
        msg += f"{i}. [{name}]({handler.ctfd.ctfd_instance}/challenges#{quote(chal['name'])}-{chal['id']}) (**{chal['category']}**){ln}"
        i += 1
    if for_discord: msg = f"## **__{title}__**{ln}" + msg
    return msg, title

async def notify_discord(msg, webhook_url: str):
    async with aiohttp.ClientSession() as session:
        try:
            webhook = Webhook.from_url(webhook_url, session=session)
        except Exception as E:
            logger.error(f"An error occurred while trying to create a webhook object: {E.__repr__()}")
            logger.error("Invalid Discord Webhook URL")
            return
        await webhook.send(msg)

def _err(msg):
    """ A small wrapper around logger.error to close program on invoke """
    logger.error(msg)
    exit(1)

def wait_until(end_datetime):
    while True:
        diff = (end_datetime - datetime.now()).total_seconds()
        if diff < 0: return       # In case end_datetime was in past to begin with
        time.sleep(diff/2)
        if diff <= 0.1: return

def parse_challenges(json_file: str, ctfd_challs: list) -> dict:

    """
        Checks if all of the challenges specified in the JSON are valid ctfd_challs. If not, errors out.
    """
    logger.info("Parsing all the specified challenges...")
    if not os.path.isfile(json_file): _err(f"{json_file} doesn't exist!")

    data = {}
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except: _err(f"Unable to read {json_file}. Invalid JSON file." )

    if data == {}: _err(f"Invalid JSON in {json_file}. Please verify")
    
    waves = [i for i in list(data.keys()) if "wave" in i.lower()]
    if waves == []: _err("wave-{IDX} not specified in JSON")

    notify = data.get("notify-discord", False)
    force_deploy = data.get("force-deploy", False)
    logger.info(f"Deploying {len(waves)} wave(s)")

    valid_challs = {}
    valid_challs["notify-discord"] = notify
    valid_challs["force-deploy"] = force_deploy
    
    for wave in waves:
        __n = wave
        valid_challs[__n] = {}
        valid_challs[__n]["challenges"] = []
        wave = data[wave]
        challs = wave["challenges"]
        for chall in challs:
            found = False
            for j in range(len(ctfd_challs)):
                srv_chall = ctfd_challs[j]
                if srv_chall["name"] == chall:
                    found = True
                    _ = {}
                    for i in ["id", "name", "category", "value"]:
                        _[i] = srv_chall[i]
                    _["state"] = handler.get_challenge_state(_["id"])
                    valid_challs[__n]["challenges"].append(_)
                    del ctfd_challs[j]
                    break
            if not found:
                logger.error(f"{chall} is an invalid challenge. It  doesn't exist in CTFd")

        # Get remaining attributes:
        for k in wave.keys():
            if "challenges" not in k.lower():
                valid_challs[__n][k] = wave[k]
    return valid_challs

async def deploy(info: dict):
    notify = info["notify-discord"]
    waves = [i for i in list(info.keys()) if "wave" in i.lower()]
    if waves == []: _err("wave-{IDX} not specified in JSON")

    for i in range(len(waves)):
        wave = waves[i]
        wave_data = info[wave]
        challs = wave_data["challenges"]

        curr_time = datetime.timestamp(datetime.now())

        deploy_time = wave_data["timestamp"]
        dt = datetime.fromtimestamp(deploy_time)

        if curr_time > deploy_time:
            logger.warning(f"{wave} was supposed to deployed on {dt}")
            if not info["force-deploy"]:
                logger.warning(f"Not deploying {wave} as `force-deploy` is set to False.")
                continue
        else:
            logger.info(f"{wave} will deployed at {dt}")
            wait_until(dt)
        
        logger.info(f"Deploying challenges of {wave} [Total challenges: {len(challs)}]")
        for chall in challs:
            if chall["state"] != "hidden":
                logger.warning(f"Challenge {chall['name']} of {wave} has already been deployed (state is marked as {chall['state']})")
                continue
            handler.unhide_challenge(chall["id"])
            logger.info(f"Deployed {chall['name']} of {wave}")

        if i < len(waves) - 1: next_time = info[waves[i+1]]["timestamp"]

        _msg = wave_data["message"]
        while "{NEXT_TIMESTAMP" in _msg:
            idx = _msg.index("{NEXT_TIMESTAMP")
            idx2 = _msg.index("}", idx)
            new_msg = _msg[idx:idx2+1].split(":")
            tz_str = new_msg[1][:-1] if len(new_msg) == 2 else "UTC"
            if len(new_msg) != 2:
                tz = pytz.timezone("UTC")
            else:
                try:
                    tz = pytz.timezone(tz_str)
                except Exception as E:
                    print(f"An error occurred when trying to get the timezone. Defaulting to UTC.\nError: {E.__repr__()}")
                    tz = pytz.timezone("UTC")
                    tz_str = "UTC"
            new_time = datetime.fromtimestamp(next_time, tz)
            _msg = _msg[:idx] + new_time.strftime("%d/%m/%Y %I:%M:%S %p") + f" {tz_str}" + _msg[idx2+1:]

        msg, title = get_notification_message(_msg, challs)
        handler.notify(msg, title)
        if info["notify-discord"]:
            msg, title = get_notification_message(_msg, challs, for_discord=True)
            await notify_discord(msg, args.discord_webhook)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CTFd Waves Release')
    parser.add_argument('--ctfd-instance', type=str, help='CTFd instance URL', default=None)
    parser.add_argument('--ctfd-token', type=str, help='CTFd admin token', default=None)
    parser.add_argument('--discord-webhook', type=str, help='Discord Webhook URL', default=None)
    parser.add_argument('--waves-file', '-f', help="Waves.JSON file that contains all the information about the waves to be released", default=None)
    args = parser.parse_args()

    args.waves_file = get_env("WAVES_FILE", curr=args.waves_file, err_msg="WAVES_FILE not set!")
    args.discord_webhook = get_env("DISCORD_WEBHOOK", curr=args.discord_webhook, err_msg="DISCORD_WEBHOOK not set!")
    
    handler = CTFd_Handler(args.ctfd_instance, args.ctfd_token)
    ctfd_challs = handler.get_challenges()
    info = parse_challenges(args.waves_file, ctfd_challs)
    asyncio.run(deploy(info))