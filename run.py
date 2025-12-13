import glob
import os
import shutil
import subprocess
from sys import argv

CWD = os.getcwd()


def info(args):
    print("\nUsage: python -m run <command> <args>")
    print("\n\tCLI tool to facilitate execution of the FitsHub project.")

    print("\nCommands:")
    print("\tinfo\t\tShow usage and help message.")
    print("\tlocal\t\tRun in local host.")
    print("\tdocker\t\tRun in Docker container (development).")
    print("\tdocker-prod\tRun in Docker container (production).")
    print("\tvagrant\t\tRun in Vagrant VM.")

    print("\nArguments:")
    print("\tFor all commands:")
    print("\t\t--no-env\t\tSkip copying .env file from examples (NOTE: .env file must be correct for the command).")
    print("\tFor local:")
    print("\t\t--socket <ip:port>\tSpecify IP:Port on which to run app (default is localhost:5000).")
    print("\tFor vagrant:")
    print("\t\t--restart\t\tRestart Vagrant VM.")
    print("\t\t--halt\t\t\tHalt Vagrant VM.")
    print("\t\t--destroy\t\tDestroy Vagrant VM.")


def vagrant(args):
    # Remove files that could cause conflicts
    shutil.rmtree(os.path.join(CWD, "uploads"), ignore_errors=True)
    shutil.rmtree(os.path.join(CWD, "rosemary.egg-info"), ignore_errors=True)

    for log in glob.glob(os.path.join(CWD, "app.log*")):
        os.remove(log)

    # Copy .env file
    if "--no-env" not in args:
        shutil.copyfile(os.path.join(CWD, ".env.vagrant.example"), os.path.join(CWD, ".env"))

    # Run Vagrant command
    os.chdir(os.path.join(CWD, "vagrant"))

    if "--restart" in args:
        subprocess.run(["vagrant", "reload", "--provision"])
    elif "--halt" in args:
        subprocess.run(["vagrant", "halt"])
    elif "--destroy" in args:
        subprocess.run(["vagrant", "destroy"])
        shutil.rmtree(os.path.join(os.getcwd(), ".vagrant"), ignore_errors=True)
    else:
        subprocess.run(["vagrant", "up", "--provision"])


def main(args):
    commands = {"info": info, "vagrant": vagrant}

    if len(args) < 2:
        info([])
    else:
        commands[args[1].strip()](args[2:])


if __name__ == "__main__":
    main(argv)
