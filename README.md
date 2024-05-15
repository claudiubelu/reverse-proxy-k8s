# Reverse Proxy Operator Charm (Kubernetes)

## Description

This charm can be used to serve as a reverse proxy for certain targets (e.g.: GitHub pages).

Note that something similar to this can be achieved in Kubernetes through `ExternalName` services, and then having an `Ingress` resource for that service (and then use an `nginx-ingress-integrator` charm). However, depending on the Ingress Operator in Kubernetes, `ExternalName`s may not be handled.

This charm instead creates a `ClusterIP` service for which an `Ingress` route can be created. This charm can also be related to an `nginx-ingress-integrator` charm for automatically creating the `Ingress` Kubernetes resource and route.

## Usage

To build this charm, run:

```bash
charmcraft pack
```

After the charm has been built, deploy it by running:

```bash
juju deploy --path ./reverse-proxy-k8s_ubuntu-22.04-amd64.charm --resource nginx-image=docker.io/nginx:1.25
```

This charm will require the `proxy-url` config option to be set (the target URL to proxy the requests to):

```bash
juju config reverse-proxy-k8s proxy-url="https://foolish.github.io" service-hostname=foo.lish.com header-host=foo.lish.com
```

This charm can be related to an `nginx-ingress-integrator` charm through the `ingress` relation. The following commands will deploy a new `nginx-ingress-integrator` charm and relate it to the `reverse-proxy-k8s` charm:

```bash
juju deploy nginx-ingress-integrator --channel stable --revision=79
juju relate nginx-ingress-integrator reverse-proxy-k8s
```

After a few moments, and if there were no issues encountered, the `reverse-proxy-k8s` charm should become Active. You should be able to reach it:

```bash
# Alternatively, you can use the set service-hostname, if it's resolvable.
curl http://unit_address
```

## Relations

This charm has an `ingress` relation, which can be provided by the `nginx-ingress-integrator` charm.

## OCI Images

This charm requires an nginx Workload Container. Example of an nginx image that can be used: `docker.io/nginx:1.25`.

## Other resources

- [Contributing](CONTRIBUTING.md) <!-- or link to other contribution documentation -->

- See the [Juju SDK documentation](https://juju.is/docs/sdk) for more information about developing and improving charms.
