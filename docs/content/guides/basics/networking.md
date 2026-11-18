# Networking

A **network** is computers connected so they can send each other data, by cable or Wi-Fi. A space with cameras, robots and servers is one: every camera sends its images to a computer, which sends results to others. This guide explains how a program finds another one on a network and talks to it, and what to check when it can't. It assumes you have done [The terminal](terminal.md); all commands run on a fresh Ubuntu install.

!!! info "To learn more"

    - [IP address](https://en.wikipedia.org/wiki/IP_address), [Domain Name System](https://en.wikipedia.org/wiki/Domain_Name_System) and [Internet protocol suite](https://en.wikipedia.org/wiki/Internet_protocol_suite): addresses, names, and the layers TCP and UDP belong to;
    - [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/): sockets, TCP and UDP, from a programmer's side.

## Servers, clients and packets

Two words come up everywhere. A **server** is a program that waits for others to contact it and answers them, such as a web site. A **client** is a program that contacts a server, such as your browser. The same computer can run both.

Data doesn't travel as one long stream: it is cut into small **packets**, each a few hundred to about 1500 bytes, each with the address it goes to, like letters in the mail. The network delivers each packet, and the receiving computer puts them back together.

## The tools

Some of the commands below may be missing on a fresh install. Install them all at once:

```shell
sudo apt update
sudo apt install -y iproute2 iputils-ping netcat-openbsd curl dnsutils
```

## Addresses

Every computer on a network has an **IP address**, its number on that network, written as four numbers from 0 to 255 separated by dots, such as `10.20.6.0`. A computer can have several, one per **network interface**: the cable port, the Wi-Fi card. List yours:

```shell
ip -br addr
```

```
lo      UNKNOWN  127.0.0.1/8 ::1/128
enp3s0  UP       10.20.5.5/16 fe80::67c:16ff:fee7:90/64
```

- Each line is an interface: its name, whether it is connected (`UP`), and its addresses. The ones with colons, such as `fe80::...`, are IPv6, a newer kind of address; this guide sticks to the older IPv4.
- `lo`, the **loopback**, is `127.0.0.1`, also called **`localhost`**: it always means "this same computer". Data sent there never leaves it, so it is how two programs on one computer talk.
- `enp3s0` is the cable, here with the address `10.20.5.5`.

The `/16` after the address is its **subnet**: of the four numbers, how much names the network rather than the computer. `/16` means the first two numbers, `10.20`, are the network, so every address from `10.20.0.0` to `10.20.255.255` is on the same local network and reached directly. `/24` would mean the first three. Addresses starting with `10.`, `172.16.` to `172.31.` and `192.168.` are **private**: they exist only inside a local network, which is why your home and the lab can both use `192.168.0.10` without trouble.

To reach anything outside the subnet, such as the internet, a computer sends its packets to the **router**, called the **default gateway**:

```shell
ip route
```

```
default via 10.20.255.254 dev enp3s0
10.20.0.0/16 dev enp3s0 proto kernel scope link src 10.20.5.5
```

Read it as: everything goes through the router at `10.20.255.254`, except the `10.20.0.0/16` network, reached directly through `enp3s0`.

## Ports

An address names a computer, but a computer runs many programs at once. A **port**, a number from 1 to 65535, names one program on it. A server **listens** on a port: it asks the computer to give it everything that arrives for that number. A client connects to an address and a port, such as `localhost:8000`.

Python, already on Ubuntu, can be a small web server, serving the files of the current folder on port 8000:

```shell
python3 -m http.server 8000 --bind 127.0.0.1
```

It keeps running and prints a line for every request. In a second terminal (++ctrl+shift+t++), be the client:

```shell
curl -I http://localhost:8000      # HTTP/1.0 200 OK: the server answered
ss -ltn                            # every port this computer listens on: LISTEN ... 127.0.0.1:8000
```

`curl` fetches an address, and `-I` asks only for the headers of the answer; `200 OK` means success. `ss -ltn` lists the listening TCP ports, as numbers. Stop the server with ++ctrl+c++ in its terminal.

`--bind 127.0.0.1` makes the server listen on the loopback only: other computers can't reach it. `--bind 0.0.0.0` would listen on every address of the computer, so others could.

Some ports are conventions everyone follows:

| Port | Protocol |
|---|---|
| 22 | SSH, a terminal on another computer |
| 53 | DNS, names to addresses |
| 80, 443 | HTTP and HTTPS, the web |
| 5672 | AMQP, message brokers such as RabbitMQ (see [Messaging](messaging.md)) |

## Names

People remember names, not numbers. **DNS**, the Domain Name System, turns a name such as `example.com` into an address. Your computer asks a DNS server, usually given by the router, unless the name is in `/etc/hosts`, a file of names known to this computer alone:

```shell
getent hosts example.com           # the address your computer would use
dig +short example.com             # ask the DNS server directly
cat /etc/hosts                     # names this computer knows by itself, such as localhost
```

Some names only exist inside one network: inside a Kubernetes cluster, for instance, every service gets a name such as `my-service.my-namespace` that doesn't exist outside it (see [Kubernetes](kubernetes.md)).

## TCP and UDP

Programs send packets with one of two **protocols**, sets of rules for the conversation.

**TCP** first opens a **connection** between the two programs, then delivers every byte, in order, resending what gets lost, or reports an error. The web, SSH and message brokers use TCP. Try it with `nc`, netcat, which sends what you type: in one terminal listen, in another connect, then type in either one and press Enter.

```shell
nc -l 9000                         # terminal 1: listen on port 9000
nc localhost 9000                  # terminal 2: connect to it
```

**UDP** sends each packet on its own, with no connection and no guarantee: a packet can be lost, or arrive out of order, and nobody notices. In return it is faster and simpler, which suits live video, where a late packet is useless anyway; industrial cameras often stream over UDP. The same test, with `-u` for UDP:

```shell
nc -u -l 9001                      # terminal 1
nc -u localhost 9001               # terminal 2
```

Stop both sides with ++ctrl+c++.

## URIs

Programs are told where to connect with a **URI**, which holds everything at once:

```
amqp://guest:guest@broker.example:5672
└┬─┘   └──┬──┘ └─┬─┘ └─────┬──────┘ └┬─┘
scheme   user  password    host     port (the scheme's default if left out)
```

The **scheme** is the protocol; the **host** is a name or an address. `https://example.com/docs` reads the same way: HTTPS, to the host `example.com`, on HTTPS's default port, 443, at the path `/docs`.

## Containers

A container, explained in [Containers](containers.md), has a network of its own, with its own addresses: `localhost` inside it means the container, not your computer. That guide shows how to open its ports to your computer, or give it your computer's network.

## When something doesn't connect

Go step by step, from the computer that fails, to find which step breaks:

```shell
ip -br addr                        # 1. am I on the network, with an address?
ping -c 3 10.20.6.0                # 2. can I reach that computer at all?
nc -zv 10.20.6.0 5672              # 3. does something listen on that port?
curl -v http://10.20.6.0:8000      # 4. does the program answer?
sudo ufw status                    # is my firewall blocking something?
```

`ping` sends a small packet and waits for the reply, three times with `-c 3`. `nc -zv` only checks whether a port accepts a connection. A **firewall** is a program that blocks some connections on purpose; `ufw` is Ubuntu's.

| Symptom | Likely cause |
|---|---|
| `ping` fails | a cable, another subnet, a router or a firewall in the way |
| `ping` works, `nc` says `Connection refused` | nothing listens on that port: the program isn't running, or uses another port |
| `nc` hangs, then times out | a firewall silently drops the packets |
| works with the address, not with the name | DNS: check `getent hosts <name>` |
| works on `localhost` only | the program listens on `127.0.0.1`: make it listen on `0.0.0.0` |

## What you learned

- A computer has an IP address per interface; `localhost` is the computer itself; the subnet says which addresses are reached directly.
- A port names a program on a computer; servers listen, clients connect.
- DNS turns names into addresses.
- TCP delivers everything in order; UDP is faster and may lose packets.
- When a connection fails, check the address, then `ping`, then the port, then the program.
