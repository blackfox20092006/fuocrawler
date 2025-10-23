import os
import subprocess
from datetime import datetime
from time import sleep
import random
import json

def git_push(foldername):
    if not os.path.isdir(foldername):
        return None
    try:
        subprocess.run(["git", "add", foldername], check=True)
        msg = f"Data uploading | {foldername} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", msg], check=False)
        subprocess.run(["git", "push"], check=True)
        return {"folder": foldername, "status": "success", "time": datetime.now().isoformat()}
    except subprocess.CalledProcessError as e:
        return {"folder": foldername, "status": "fail", "error": str(e), "time": datetime.now().isoformat()}

if __name__ == "__main__":
    folders = [f for f in os.listdir() if os.path.isdir(f)]
    random.shuffle(folders)
    log = []
    for folder in folders:
        result = git_push(folder)
        if result:
            log.append(result)
        sleep(random.randint(10, 30))
    with open("push_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
