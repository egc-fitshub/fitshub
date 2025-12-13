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
    print("\tFor docker:")
    print("\t\t--stop\t\t\tStops the containers.")
    print("\tFor docker-prod:")
    print("\t\t--stop\t\t\tStops the containers.")

def copy_env(env, args):
    if "--no-env" not in args:
        shutil.copyfile(os.path.join(CWD, f".env.{env}.example"), os.path.join(CWD, ".env"))


def local(args):
    # Copy .env file
    copy_env("local", args)

    # Run Flask app
    command = ["flask", "run", "--debug", "--reload"]

    for i in range(len(args)):
        if args[i] == "--socket":
            host, port = (c.strip() for c in args[i + 1].split(":"))
            command.extend(["-h", host])
            command.extend(["-p", port])

    subprocess.run(command)

def docker(args):
    # Copy .env file
    copy_env("docker", args)

    # Run Flask app
    if "--stop" in args:
        subprocess.run(["docker", "compose", "-f", "docker/docker-compose.dev.yml", "down"])
    else:
        subprocess.run(["docker", "compose", "-f", "docker/docker-compose.dev.yml", "up", "-d", "--build", "--remove-orphans"])

def docker_prod(args):
    # Copy .env file
    copy_env("docker.production", args)

    # Run Flask app
    if "--stop" in args:
        subprocess.run(["docker", "compose", "-f", "docker/docker-compose.prod.yml", "down"])
    else:
        subprocess.run(["docker", "compose", "-f", "docker/docker-compose.prod.yml", "up", "-d", "--build", "--remove-orphans"])


def vagrant(args):
    # Remove files that could cause conflicts
    shutil.rmtree(os.path.join(CWD, "uploads"), ignore_errors=True)
    shutil.rmtree(os.path.join(CWD, "rosemary.egg-info"), ignore_errors=True)

    for log in glob.glob(os.path.join(CWD, "app.log*")):
        os.remove(log)

    # Copy .env file
    copy_env("vagrant", args)

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
    commands = {"info": info, "local": local, "docker": docker, "docker-prod": docker_prod, "vagrant": vagrant}

    if len(args) < 2:
        info([])
    else:
        commands[args[1].strip()](args[2:])


if __name__ == "__main__":
    main(argv)
