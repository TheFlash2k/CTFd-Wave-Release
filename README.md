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
