from plugins.kubernetes.k8s_api import main as runner
from textwrap import dedent
import os, utils

os.mkdir('out')
auth = utils.auth['plugins']['kubernetes']
with open('src/kubeconfig', 'w') as stream:
    clusters = ''
    users = ''
    contexts = ''
    for cluster in auth:
        clusters += f"""
        - cluster:
            server: {auth[cluster]['server']}
            name: {cluster}"""

        users += f"""
        - name: {cluster}
            user:
            token: {auth[cluster]['token']}
        """

        contexts += f"""
        - context:
            cluster: {cluster}
            user: {cluster}
            name: {cluster}
        """

        current = cluster

    stream.write(dedent(f"""
    apiVersion: v1
    Kind: Config
    current-context: {current}
    preferences: {{}}
    clusters: {clusters}
    users: {users}
    contexts: {contexts}
    """))

    for type in ('workers, apps'):
        with open(f'src/{type}.xml','w') as stream:
            stream.write(dedent(f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE {type} [
            <!ENTITY json SYSTEM "{type}.json">
            ]>
            <{type}>&json;</{type}>""").strip())