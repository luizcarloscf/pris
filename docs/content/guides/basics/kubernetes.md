# Kubernetes

[Containers](containers.md) run one program on one computer. A real system runs dozens of them on several computers, and someone has to decide which computer runs which, restart a program when it crashes or a computer dies, start more copies when the load grows, and let the programs find each other. [Kubernetes](https://kubernetes.io/docs/concepts/overview/) does that. You describe what should run, in text files, and Kubernetes keeps the computers that way, all the time. This guide runs Kubernetes on a single computer with [minikube](https://minikube.sigs.k8s.io/docs/start/), on a fresh Ubuntu install. It assumes you have done [Containers](containers.md) and [Networking](networking.md).

!!! info "To learn more"

    - [Kubernetes basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/): the official interactive tutorial;
    - [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Services](https://kubernetes.io/docs/concepts/services-networking/service/) and [ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/): the objects of this guide;
    - [kubectl quick reference](https://kubernetes.io/docs/reference/kubectl/quick-reference/) and [debugging pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/).

## Clusters and nodes

The computers Kubernetes manages together form a **cluster**; each computer is a **node**. A few programs, the **control plane**, hold what you asked for and keep comparing it with what actually runs: when they differ, they act, starting or stopping containers until both match again. You never tell Kubernetes "start this container on that computer"; you tell it "there should be two copies of this", and it works out the rest.

minikube makes a cluster of one node, inside a container on your computer: enough to learn everything here. On a real cluster, the files and commands are the same.

## Installing

minikube needs [Docker](containers.md#installing). Then install minikube itself, and **kubectl**, the command you use to talk to any cluster (see [Install kubectl on Linux](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/) for other ways):

```shell
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
sudo snap install kubectl --classic
minikube start                     # creates the cluster and tells kubectl about it
kubectl get nodes                  # minikube   Ready   control-plane
```

- `curl -LO` downloads a file and keeps its name; `sudo install` copies it into `/usr/local/bin`, a folder where the terminal finds programs (see [The terminal](terminal.md#environment-variables)), and makes it runnable.
- `snap` is another way Ubuntu installs programs, besides apt.
- `minikube start` takes a minute or two the first time: it downloads the cluster's images.

## Objects and YAML

Everything in a cluster is an **object**, of some **kind**:

| Kind | What it is |
|---|---|
| **Pod** | one or more containers that run together, on one node: the unit Kubernetes starts and stops |
| **Deployment** | "keep this many identical pods running": it creates them, replaces those that die, and updates them when the image changes |
| **Service** | a fixed name and address in front of a group of pods, which spreads the connections between them |
| **ConfigMap** | files or settings for the pods, kept apart from the image |
| **Namespace** | a folder for objects: names must be unique only inside one |

You rarely create pods yourself: a Deployment makes them, and replaces them when they die.

Objects are described in **YAML**, a way to write structured data as indented text. Three rules are enough to read it:

- `key: value` sets a field: `replicas: 2`.
- Indentation, with spaces (never tabs), puts fields inside others, like folders: below, `name` is inside `metadata`.
- Lines starting with `- ` are items of a list.

`---` separates several objects in one file.

## A first application

Save this as `web.yaml`. It describes four objects: a namespace, a ConfigMap with a web page, a Deployment of two nginx pods that serve it, and a Service in front of them.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: demo
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: web
  namespace: demo
data:
  index.html: |
    <h1>Hello from Kubernetes</h1>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
          resources:
            limits:
              cpu: 250m
              memory: 128Mi
          volumeMounts:
            - name: site
              mountPath: /usr/share/nginx/html
      volumes:
        - name: site
          configMap:
            name: web
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: demo
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
```

Reading it:

- Every object has an `apiVersion` and a `kind`, and a `metadata` with its `name` and, except the namespace itself, the `namespace` it lives in.
- The ConfigMap's `data` holds one file, `index.html`; `|` means "the indented lines below, as text".
- The Deployment's `spec`, its specification, asks for `replicas: 2` pods. `template` is what each pod looks like: one container from the image `nginx:1.27`, listening on port 80.
- `volumes` and `volumeMounts` put the ConfigMap's files in the folder nginx serves, `/usr/share/nginx/html`, like `-v` with Docker (see [Containers](containers.md#files-and-settings)).
- `limits` caps what each container may use: `250m` is a quarter of a CPU, `128Mi` 128 megabytes of memory.
- **Labels** tie it all together: each pod gets the label `app: web`, the Deployment's `selector` finds its pods by that label, and so does the Service, which sends connections to every pod labeled `app: web`.

## Running it

```shell
kubectl apply -f web.yaml
kubectl -n demo get pods           # two pods web-..., STATUS Running
kubectl -n demo get service web
kubectl -n demo port-forward service/web 8080:80
```

- `kubectl apply -f web.yaml` sends the file to the cluster, which creates the objects.
- `-n demo` means "in the namespace demo"; without it, kubectl looks in the namespace `default`.
- `get pods` lists the pods: give them a few seconds to go from `ContainerCreating` to `Running`.
- `port-forward` forwards port 8080 of your computer to the Service, for as long as it runs.

While the port-forward runs, `curl http://localhost:8080` in another terminal answers `<h1>Hello from Kubernetes</h1>`, from one of the two pods. Stop the port-forward with ++ctrl+c++.

`kubectl apply` is **declarative**: the file says what you want, not what to do. Change `replicas: 2` to `3`, apply the file again, and a third pod appears; nothing else changes. Delete a pod, `kubectl -n demo delete pod <name>` with a name from `get pods`, and watch `get pods` again: the Deployment starts a new one at once, since two must be running.

## Names inside the cluster

Pods come and go, each new one with a new address. A Service keeps one name. From any pod of the cluster, the Service above is `web.demo`, which is `<service>.<namespace>`, or just `web` from inside the same namespace. Try it from a temporary pod that only runs `curl`:

```shell
kubectl -n demo run client --rm -it --image=curlimages/curl:8.11.1 --restart=Never -- curl -s http://web
```

To reach a Service from outside the cluster, use `kubectl port-forward` while developing, or make it `type: NodePort`, which opens a port, between 30000 and 32767, on every node of the cluster.

## Changing settings

A pod reads its ConfigMap's files when it starts. After editing the page in `web.yaml`, apply the file and restart the pods; the Deployment replaces them one at a time, so the site never goes down:

```shell
kubectl apply -f web.yaml
kubectl -n demo rollout restart deployment/web
```

## Your own images

The cluster downloads images from a registry. An image you built on your own computer, such as the `hello:0.1.0` of [Containers](containers.md#building-an-image), isn't in any registry, so load it into minikube first:

```shell
minikube image load hello:0.1.0
```

and give its container `imagePullPolicy: IfNotPresent`, next to its `image`, so the cluster uses the image it has instead of looking for it in a registry.

## When a pod doesn't run

```shell
kubectl -n demo get pods                   # the STATUS of each pod
kubectl -n demo describe pod <name>        # everything about it; its events are at the end
kubectl -n demo logs <name>                # what its container printed
kubectl -n demo exec -it <name> -- sh      # a shell inside it
```

| STATUS | Likely cause |
|---|---|
| `Pending` | no node has the CPU or memory it asks for |
| `ContainerCreating`, for long | a ConfigMap or volume it mounts doesn't exist |
| `ImagePullBackOff` | a wrong image name or tag, or a local image not loaded |
| `CrashLoopBackOff` | the program exits right after starting, and Kubernetes keeps restarting it: read `kubectl logs` |

## Cleaning up

```shell
kubectl delete namespace demo      # removes the namespace and everything in it
minikube stop                      # stops the cluster; minikube delete removes it
```

## What you learned

- A cluster is a group of nodes; you declare what should run, and the control plane keeps it so.
- Pods run containers; Deployments keep a number of pods running; Services give them a fixed name; ConfigMaps hold their settings.
- Objects are YAML files, sent with `kubectl apply`; labels connect them.
- `get`, `describe` and `logs` tell why a pod doesn't run.
