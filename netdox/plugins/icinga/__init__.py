from plugins.icinga.api import runner
stage = 'other'

import utils
icinga_hosts = utils.auth()['plugins']['icinga']