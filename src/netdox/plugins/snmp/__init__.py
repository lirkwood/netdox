from netdox.app import LifecycleStage
from netdox.plugins.snmp.footer import runner
from netdox.plugins.snmp.objs import SNMPExplorer, Job

__stages__ = {
    LifecycleStage.FOOTERS: runner
}