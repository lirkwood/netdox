from netdox import Network
from netdox.plugins.ps_k8s import footers

net = Network.fromDump()
footers(net)
print(net.domains['ag-budget-poc.allette.com.au'].node.to_psml())