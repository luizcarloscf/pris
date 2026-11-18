# Containers

A program rarely runs alone: it needs a certain version of Python, some libraries, some files. Install it on another computer and something is always a little different, and "it works on my computer" stops being true. A **container** solves that: it packs a program with everything it needs into an **image**, and runs it isolated from the rest of the computer, the same way on a laptop, a lab computer or a cluster. This guide uses [Docker](https://docs.docker.com/get-started/), the most common tool for containers, on a fresh Ubuntu install. It assumes you have done [The terminal](terminal.md) and [Networking](networking.md).

!!! info "To learn more"

    - [Docker's getting started](https://docs.docker.com/get-started/): images, containers and registries;
    - [Dockerfile reference](https://docs.docker.com/reference/dockerfile/): every instruction of a Dockerfile;
    - [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/): smaller images;
    - [Docker networking](https://docs.docker.com/engine/network/) and [bind mounts](https://docs.docker.com/engine/storage/bind-mounts/).

## Images and containers

Think of an **image** as a frozen, read-only copy of a small computer's disk: an operating system, a program and its libraries, ready to start. A **container** is that image running: a process on your computer that sees only the image's files, its own network and its own list of processes, as if it were a separate computer. Start ten containers from one image and you get ten independent copies; stop them and the image is unchanged.

Unlike a virtual machine, a container doesn't run a second operating system: it shares your computer's, which is why it starts in a second and takes little memory.

Images are named `<name>:<tag>`, such as `ubuntu:24.04`, where the **tag** is usually a version. They come from a **registry**, a library of images online; Docker's default is [Docker Hub](https://hub.docker.com).

## Installing

Docker's convenience script installs Docker from Docker's own packages (see [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) for the step-by-step way):

```shell
sudo apt update
sudo apt install -y curl
curl -fsSL https://get.docker.com -o get-docker.sh     # download the script
sudo sh get-docker.sh                                  # run it, as administrator
sudo usermod -aG docker $USER                          # let your user run docker without sudo
```

The last line adds you to the `docker` group, which is allowed to use Docker. It only applies after you log out and back in (see [Linux post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/)). Then check:

```shell
docker run --rm hello-world
```

Docker downloads the tiny `hello-world` image, runs it, and it prints `Hello from Docker!` with an explanation of what just happened.

## A first container

```shell
docker run --rm -it ubuntu:24.04 bash
```

This downloads Ubuntu 24.04's image, the first time only, and opens a terminal inside a container made from it. The prompt changes, to something like `root@3f2a1b4c5d6e:/#`: you are inside. Run `ls /`, `cat /etc/os-release`: it looks like a whole Ubuntu, but it's only the image's files. Type `exit` to leave; the container stops.

- `run` creates a container from an image and starts it; `bash`, at the end, is the command to run inside, here a shell.
- `--rm` deletes the container when it stops, so stopped containers don't pile up.
- `-it` connects your keyboard and screen to it, for an interactive program like a shell.

`docker images` lists the images on your computer. Pin the tag, `nginx:1.27` rather than `nginx` or `nginx:latest`: `latest` points to whatever is newest when you download it, so the same command could give a different program next month.

## Running a server

**nginx** is a web server. Run it in the background and visit it:

```shell
docker run -d --name web -p 8080:80 nginx:1.27
curl http://localhost:8080         # nginx's welcome page, as HTML
docker ps                          # the running containers: web, nginx:1.27, 0.0.0.0:8080->80/tcp
docker logs web                    # what it printed: one line per request
docker stop web                    # stop it
docker rm web                      # delete it
```

- `-d`, detached, runs it in the background and gives you the prompt back.
- `--name web` names it, so the other commands can refer to it.
- `-p 8080:80` **publishes** a port. nginx listens on port 80 inside the container, on the container's own network, which your computer can't see; `-p 8080:80` forwards port 8080 of your computer to it. Open <http://localhost:8080> in a browser too.

## Files and settings

A container's files belong to it: whatever it writes is lost when the container is removed, and it can't see your files. To share a folder with it, **mount** the folder over one of its own. To give it settings, pass **environment variables** (see [The terminal](terminal.md#environment-variables)):

```shell
mkdir site && echo '<h1>Hello from a container</h1>' > site/index.html
docker run -d --name web -p 8080:80 -v "$PWD/site:/usr/share/nginx/html:ro" nginx:1.27
curl http://localhost:8080         # <h1>Hello from a container</h1>
docker rm -f web                   # stop and delete it at once

docker run --rm -e GREETING=hi ubuntu:24.04 sh -c 'echo $GREETING'    # hi
```

- `-v <your folder>:<its folder>` mounts a folder: nginx serves the files of `/usr/share/nginx/html`, which is now your `site` folder. `$PWD` is the current folder's full path; a mount needs a full path. `:ro` makes it read-only for the container.
- `-e GREETING=hi` sets an environment variable inside the container.

This is how one image serves many uses: the program is in the image, and each place gives it its own files and settings.

## Building an image

To ship your own program, describe its image in a **Dockerfile**: a text file of instructions, run one after another. In a new folder, save a program as `app.py`:

```python
import os
import socket

print("Hello from", socket.gethostname(), "with GREETING =", os.environ.get("GREETING", "none"))
```

and this as `Dockerfile`, with no extension:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
```

Build it, then run it:

```shell
docker build -t hello:0.1.0 .
docker run --rm -e GREETING=hi hello:0.1.0    # Hello from 7cd2244feaf5 with GREETING = hi
```

- `FROM` starts from an existing image, here a small Debian with Python 3.12.
- `WORKDIR /app` creates the folder `/app` and makes it the current folder for what follows.
- `COPY app.py .` copies your file into it.
- `CMD` is the command a container of this image runs when it starts.
- `docker build -t hello:0.1.0 .` builds the image and names it; the final `.` is the **build context**, the folder whose files `COPY` can use.
- The name printed after `Hello from` is the container's id, used as its hostname: each container is its own computer on the network.

Each instruction makes a **layer**, and Docker reuses the layers that didn't change: build again and it's instant. So put what changes least, such as installing libraries, before what changes most, your code. A `.dockerignore` file, like a list of names, keeps things such as `.venv` or `.git` out of the build context.

## Networks

Containers on the same Docker network reach each other by their names, without publishing any port:

```shell
docker network create demo
docker run -d --name web --network demo nginx:1.27
docker run --rm --network demo curlimages/curl:8.11.1 -s http://web    # nginx's page
docker rm -f web && docker network rm demo
```

The second container, which only runs `curl`, reaches the first one as `http://web`: Docker gives every container on the network a name.

With `--network host`, a container skips its own network and uses your computer's directly: no `-p` is needed, its ports are your computer's, and `localhost` inside it is your computer. Programs that must find devices on the local network, such as cameras, or that use many ports, run this way.

## Cleaning up

Images take disk space, often hundreds of megabytes each:

```shell
docker system df                   # how much space images and containers use
docker container prune             # remove the stopped containers
docker image prune                 # remove images no container uses
```

## What you learned

- An image packs a program with everything it needs; a container is an image running, isolated.
- `docker run` starts one: `-it` to use it interactively, `-d` in the background, `-p` to publish a port, `-v` to mount a folder, `-e` to set a variable.
- A Dockerfile describes an image, built in cached layers with `docker build`.
- Containers on one network reach each other by name; `--network host` gives a container your computer's network.
