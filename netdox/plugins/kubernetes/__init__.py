from plugins.kubernetes.k8s_api import main as runner
from textwrap import dedent
import os, utils
stage = 'resource'

# Create output dir
for dir in ('out', 'src'):
  if not os.path.exists(f'plugins/kubernetes/{dir}'):
      os.mkdir(f'plugins/kubernetes/{dir}')

auth = utils.auth()['plugins']['kubernetes']
with open('plugins/kubernetes/src/kubeconfig', 'w') as stream:
    clusters = ''
    users = ''
    contexts = ''
    for context in auth:
        clusters += f"""
        - cluster:
            server: {auth[context]['server']}/k8s/clusters/{auth[context]['clusterId']}
          name: {context}"""

        users += f"""
        - name: {context}
          user:
            token: {auth[context]['token']}
        """

        contexts += f"""
        - context:
            cluster: {context}
            user: {context}
          name: {context}
        """

        current = context

        stream.write(dedent(f"""
        apiVersion: v1
        Kind: Config
        current-context: {current}
        preferences: {{}}
        clusters: {clusters}
        users: {users}
        contexts: {contexts}
        """))

for type in ('workers', 'apps'):
    with open(f'plugins/kubernetes/src/{type}.xml','w') as stream:
        stream.write(dedent(f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE {type} [
        <!ENTITY json SYSTEM "{type}.json">
        ]>
        <{type}>&json;</{type}>""").strip())