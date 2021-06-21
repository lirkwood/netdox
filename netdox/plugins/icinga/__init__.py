import utils
stage = 'post-write'
global icinga_hosts
icinga_hosts = {}
def init():
    global icinga_hosts
    icinga_hosts = utils.auth()['plugins']['icinga']

from plugins.icinga.api import runner