from __future__ import annotations
from typing import Iterable, Optional

from bs4 import Tag
from netdox import psml, utils
from netdox import Network
from netdox.dns import IPv4Address
from netdox.nodes import ProxiedNode
from dataclasses import dataclass

@dataclass
class Deployment:
    """K8s deployment."""
    name: str
    """Name of this deployment."""
    labels: dict[str, str]
    """Some labels applied to this deployment."""
    selector: dict[str, str]
    """Labels that this deployment will match against for pods"""
    containers: list[Container]
    """The containers specified by this deployment."""

@dataclass
class Container:
    """Docker container."""
    name: str
    """Name of this container."""
    image: str
    """URI of the image this container runs."""
    volumes: list[MountedVolume]
   
@dataclass(frozen = True)
class MountedVolume:
    """Volume from a persistent volume claim mounted in a Container."""
    pvc: str
    """Name of the persistent volume claim this volume is from."""
    sub_path: str
    """Path to the mount point in PVC."""
    mount_path: str
    """Path to the mount point in container."""

@dataclass
class Service:
    """K8s service."""
    name: str
    """Name of this service."""
    labels: dict[str, str]
    """Some labels applied to this service."""
    selector: dict[str, str]
    """Labels that this service will match against for deployments."""
    paths: set[str]
    """Some ingress paths that resolve to this service."""


@dataclass
class Pod:
    """K8s pod."""
    name: str
    """Name of this pod."""
    labels: dict[str, str]
    """Some labels applied to this pod."""
    workerName: str
    """Name of this pod's host worker."""
    workerIp: str
    """CIDR IPv4 address of this pod's host worker."""
    rancher: Optional[str]
    """Link to this pod on rancher."""

    @classmethod
    def from_k8s_V1Pod(cls, pod) -> Pod:
        return cls(
            pod.metadata.name,
            pod.metadata.labels,
            pod.spec.node_name,
            pod.status.host_ip,
            None
        )

@dataclass
class Cluster:
    name: str
    """Name of this cluster."""
    node_ips: set[str]
    """Set of IPv4 addresses (as strings) 
    that resolve to nodes used in this cluster."""
    location: Optional[str]
    """Location of this cluster."""

    def __init__(self, 
            name: str, 
            node_ips: Iterable[str], 
            location: Optional[str] = None
        ) -> None:
        self.name = name
        self.location = location
        self.node_ips = set(node_ips) | set(
            utils.config('k8s')[self.name]['proxies'])


class App(ProxiedNode):
    """
    Kubernetes app from a namespaced deployment
    """
    cluster: Cluster
    """Cluster this app is running in"""
    paths: set[str]
    """Ingress paths that resolve to this node. 
    Only includes paths starting on domains that also resolve to a configured proxy IP."""
    pod_labels: dict
    """Labels applied to the pods"""
    template: list[Container]
    """Template pods are started from"""
    pods: list[Pod]
    """A list of pods running this app"""
    type: str = 'k8sapp'

    ## dunder methods

    def __init__(self, 
            network: Network,
            name: str, 
            cluster: Cluster, 
            paths: Optional[Iterable[str]] = None,
            labels: Optional[dict] = None, 
            pods: Optional[Iterable[Pod]] = None, 
            template: Optional[Iterable[Container]] = None
        ) -> None:
        domains = {path.split('/')[0] for path in (paths if paths else [])}
        for domain in list(domains):
            resolved = False
            for ipv4 in cluster.node_ips:
                if network.resolvesTo(domain, ipv4):
                    resolved = True
            if not resolved: domains.remove(domain)

        super().__init__(
            network = network, 
            name = name,
            identity = cluster.name +'_'+ name,
            domains = domains,
            ips = []
        )
        
        self.paths = set(paths) if paths else set()
        self.cluster = cluster
        self._location = cluster.location
        self.pod_labels = labels or {}
        self.pods = list(pods) if pods else []
        self.template = list(template) if template else []

    ## abstract properties
    
    @property
    def psmlBody(self) -> list[psml.Section]:
        return [self.psmlPodTemplate, self.psmlRunningPods]

    ## properties

    @property
    def psmlPodTemplate(self) -> psml.Section:
        section = psml.Section('template', 'Pod Template')
        count = 0
        for container in self.template:
            frag = psml.PropertiesFragment(id = 'container_' + str(count), properties = [
                psml.Property(name = 'container', title = 'Container Name', value = container.name),
                psml.Property(name = 'image', title = 'Image ID', value = container.image)
            ])
            for volume in container.volumes:
                frag.extend([
                    psml.Property(
                        name = 'pvc', 
                        title = 'Persistent Volume Claim', 
                        value = volume.pvc
                    ),
                    psml.Property(
                        name = 'mount_path', 
                        title = 'Path in Container', 
                        value = volume.mount_path
                    ),
                    psml.Property(
                        name = 'sub_path', 
                        title = 'Path in PVC', 
                        value = volume.sub_path
                    )
                ])

            section.insert(frag)
            count += 1
        return section
                
    @property
    def psmlRunningPods(self) -> psml.Section:
        section = psml.Section('pods', 'Running Pods')
        count = 0
        for pod in self.pods:
            workerIp = None
            if pod.workerIp is not None:
                workerIp = self.network.find_dns(pod.workerIp)
            section.insert(psml.PropertiesFragment(
                id = 'pod_' + str(count), 
                properties = [
                    psml.Property(name = 'pod', title = 'Pod', value = pod.name),

                    psml.Property(name = 'ipv4', title = 'Worker IP', 
                        value = (psml.XRef(docid = workerIp.docid)
                            if workerIp else '—')),

                    psml.Property(name = 'worker_node', title = 'Worker Node', 
                        value = (psml.XRef(docid = workerIp.node.docid)
                            if workerIp and workerIp.node else '—')),

                    psml.Property(name = 'rancher', title="Pod on Rancher", 
                        value = psml.Link(pod.rancher) if pod.rancher else '—')
                ]
            ))
            count += 1
        return section
