from __future__ import annotations
from typing import Iterable, Optional

from bs4 import Tag
from netdox import psml, utils
from netdox import Network
from netdox.nodes import ProxiedNode
from dataclasses import dataclass

@dataclass
class Deployment:
    """K8s deployment."""
    name: str
    """Name of this deployment."""
    labels: dict[str, str]
    """Some labels applied to this deployment."""
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
class Pod:
    """K8s pod."""
    name: str
    """Name of this pod."""
    workerName: str
    """Name of this pod's host worker."""
    workerIp: str
    """CIDR IPv4 address of this pod's host worker.'"""
    rancher: Optional[str]
    """Link to this pod on rancher."""

    @classmethod
    def from_k8s_V1Pod(cls, pod) -> Pod:
        return cls(
            pod.metadata.name,
            pod.spec.node_name,
            pod.status.host_ip,
            None
        )


class App(ProxiedNode):
    """
    Kubernetes app from a namespaced deployment
    """
    cluster: str
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
            cluster: str, 
            paths: Iterable[str] = None,
            labels: dict = None, 
            pods: Iterable[Pod] = None, 
            template: Iterable[Container] = None
        ) -> None:
        proxies = [proxy for proxy in utils.config('k8s')[cluster]['proxies']]
        domains = {p.split('/')[0] for p in sorted(paths if paths else [], key = len)}
        for domain in list(domains):
            if not any([network.resolvesTo(domain, proxy) for proxy in proxies]):
                domains.remove(domain)

        super().__init__(
            network = network, 
            name = name,
            identity = cluster +'_'+ name,
            domains = domains,
            ips = []
        )
        
        self.paths = set(paths) if paths else set()
        self.cluster = cluster
        self.pod_labels = labels or {}
        self.pods = list(pods) if pods else []
        self.template = list(template) if template else []

    ## abstract properties
    
    @property
    def psmlBody(self) -> list[Tag]:
        return [self.psmlPodTemplate, self.psmlRunningPods]

    ## properties

    @property
    def psmlPodTemplate(self) -> Tag:
        section = Tag(is_xml=True, name='section', attrs={'id':'template', 'title':'Pod Template'})
        count = 0
        for container in self.template:
            frag = psml.PropertiesFragment(id = 'container_' + str(count), properties = [
                psml.Property(name = 'container', title = 'Container Name', value = container.name),
                psml.Property(name = 'image', title = 'Image ID', value = container.image)
            ])
            for volume in container.volumes:
                frag.append(psml.Property(
                    name = 'pvc', 
                    title = 'Persistent Volume Claim', 
                    value = volume.pvc
                ))
                frag.append(psml.Property(
                    name = 'mount_path', 
                    title = 'Path in Container', 
                    value = volume.mount_path
                ))
                frag.append(psml.Property(
                    name = 'sub_path', 
                    title = 'Path in PVC', 
                    value = volume.sub_path
                ))

            section.append(frag)
            count += 1
        return section
                
    @property
    def psmlRunningPods(self) -> Tag:
        section = Tag(is_xml=True, name='section', attrs={'id':'pods', 'title':'Running Pods'})
        count = 0
        for pod in self.pods:
            workerIp = self.network.find_dns(pod.workerIp)
            section.append(psml.PropertiesFragment(id = 'pod_' + str(count), properties = [
                psml.Property(name = 'pod', title = 'Pod', value = pod.name),

                psml.Property(name = 'ipv4', title = 'Worker IP', 
                    value = psml.XRef(docid = workerIp.docid)),

                psml.Property(name = 'rancher', title="Pod on Rancher", 
                    value = psml.Link(pod.rancher) if pod.rancher else '—'),

                psml.Property(name = 'worker_node', title = 'Worker Node', 
                    value = (psml.XRef(docid = workerIp.node.docid)
                        if workerIp.node else '—'))
            ]))
            count += 1
        return section
