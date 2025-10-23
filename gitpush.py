import os
import random
import subprocess
from datetime import datetime
from time import sleep
def git_push():

    subprocess.run(["git", "add", "."], check=True)
    msg = 'Data uploading' + " | " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    subprocess.run(["git", "commit", "-m", msg], check=False)

    subprocess.run(["git", "push"], check=True)

if __name__ == "__main__":
    while True:
        git_push()
        sleep(30)