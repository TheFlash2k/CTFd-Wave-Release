# CTFd-Wave-Release
A Simple CTFd add-on that will be used to release challenges in a sort of `wave`.

---

## Usage:

```bash
./wave-release.py -f sample.json
```

### NOTE:
You will need to specify the variables in the .env or by command line arguments.

There is a `NEXT_TIMESTAMP` variable that can be defined inside the `.json` file specifically in the messages block, that will reflect in both CTFd and Discord.

---

### Variables:

#### force-deploy:
If set to true, this will deploy the challenges if the time of deployment of has passed.

#### notify-discord:
If set to true, it will use the `DISCORD_WEBHOOK` environment variable to send the notification to the specific discord channel.
