#!/usr/bin/env python3

import argparse
import json
from pprint import pprint
import os
import discord
from datetime import datetime
import time

from utils.ctfd import CTFd
from utils.handler import RequestHandler, Mode
from utils.logger import logger, logging

class CTFd_Handler:
    """ This class' methods will be used for interaction with the CTFd instance. """
    def __init__(self, instance: str, token: str):
        self.ctfd = CTFd(instance=instance, token=token)
    
    def get_challenges(self) -> list:
        """ Returns the list of all the challenges currently deployed
        """
        return RequestHandler.MakeRequest(
            mode=Mode.GET,
            url=f"{self.ctfd.ctfd_instance}/api/v1/challenges?view=admin",
            token=self.ctfd.ctfd_token
        ).json()["data"]
    
    def __modify_challenge__(self, id: int, mode: str):
        return RequestHandler.MakeRequest(
            mode=Mode.PATCH,
            url=f"{self.ctfd.ctfd_instance}/api/v1/challenges/{id}",
            token=self.ctfd.ctfd_token,
            json={ "state": mode }
        ).json()["data"]

    def get_challenge_state(self, id: int):
        return RequestHandler.MakeRequest(
            mode=Mode.GET,
            url=f"{self.ctfd.ctfd_instance}/api/v1/challenges/{id}",
            token=self.ctfd.ctfd_token
        ).json()["data"]["state"]

    def unhide_challenge(self, id: int):
        return self.__modify_challenge__(id, "visible")
    
    def hide_challenge(self, id: int):
        return self.__modify_challenge__(id, "hidden")

    def notify(self, msg: str, challs: list = None):
        msg = f"**{msg}**"
        msg += "\n\n Following challenges have been released:\n\n"
        i = 1
        for chal in challs:
            msg += f"{i}. [{chal['name']}]({self.ctfd.ctfd_instance}/challenges#{chal['name']}-{chal['id']}) (**{chal['category']}**)\n\n"
            i += 1

        return RequestHandler.MakeRequest(
            mode=Mode.POST,
            url=f"{self.ctfd.ctfd_instance}/api/v1/notifications",
            token=self.ctfd.ctfd_token,
            json={"title": "New Wave Released", "content": msg}
        ).json()

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

    """ Checks if all of the challenges specified in the JSON are valid ctfd_challs. If not, errors out.
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

def deploy(info: dict):
    notify = info["notify-discord"]
    waves = [i for i in list(info.keys()) if "wave" in i.lower()]
    if waves == []: _err("wave-{IDX} not specified in JSON")

    if not os.path.isfile(".deployed"):
        with open(".deployed", "w") as f: f.write("")

    for i in range(len(waves)):
        wave = waves[i]
        with open(".deployed", "r") as f:
            for line in f.readlines():
                logger.info(f"{wave} has already been deployed!")
                continue
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
                print(f"Challenge {chall['name']} of {wave} has already been deployed (state is marked as {chall['state']})")
                continue
            handler.unhide_challenge(chall["id"])
            logger.info(f"Deployed {chall['name']} of {wave}")
        
        if i < len(waves) - 1: next_time = info[waves[i+1]]["timestamp"]
        msg = wave_data["message"].replace("NEXT_TIMESTAMP", str(datetime.fromtimestamp(next_time)))
        handler.notify(msg, challs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CTFd Waves Release')
    parser.add_argument('--ctfd-instance', type=str, help='CTFd instance URL', default=None)
    parser.add_argument('--ctfd-token', type=str, help='CTFd admin token', default=None)
    parser.add_argument('--discord-webhook', type=str, help='Discord Webhook URL', default=None)
    parser.add_argument('--waves-file', '-f', help="Waves.JSON file that contains all the information about the waves to be released", required=True)
    args = parser.parse_args()

    handler = CTFd_Handler(args.ctfd_instance, args.ctfd_token)
    ctfd_challs = handler.get_challenges()
    info = parse_challenges(args.waves_file, ctfd_challs)
    deploy(info)