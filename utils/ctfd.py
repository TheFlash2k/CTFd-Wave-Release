from .logger import logger
from .handler import RequestHandler, Mode
from .utils import get_env

class CTFd:
    def __init__(self, instance: str, token: str):
        
        self.ctfd_instance = get_env(key="CTFD_INSTANCE", curr=instance, err_msg="CTFD_INSTANCE URL is not set")
        self.ctfd_token    = get_env(key="CTFD_ADMIN_TOKEN", curr=token, err_msg="CTFD_ADMIN_TOKEN is not set")

        if len(self.ctfd_instance) == 0 or len(self.ctfd_token) == 0:
            logger.error("CTFd instance or token is not set.")
            exit(1)

        if self.ctfd_instance[-1] == "/":
            self.ctfd_instance = self.ctfd_instance[:-1]
        
        if self.ctfd_instance[:7] != "http://" and self.ctfd_instance[:8] != "https://":
            self.ctfd_instance = "http://" + self.ctfd_instance

        logger.info(f"CTFd instance: {self.ctfd_instance}")
        logger.info(f"Checking connection to CTFd version.")
        if not self.is_working():
            logger.error("CTFd instance is not working.")
            exit(1)
        else:
            logger.info("CTFd instance is working.")

    def is_working(self):
        r = RequestHandler.MakeRequest(
            mode=Mode.GET,
            url=f"{self.ctfd_instance}/api/v1/users",
            token=self.ctfd_token
        )
        return r.status_code == 200
    
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

    def notify(self, msg: str, title: str):
        return RequestHandler.MakeRequest(
            mode=Mode.POST,
            url=f"{self.ctfd.ctfd_instance}/api/v1/notifications",
            token=self.ctfd.ctfd_token,
            json={"title": title, "content": msg}
        ).json()