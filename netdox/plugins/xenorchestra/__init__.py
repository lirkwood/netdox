from plugins.xenorchestra.xo_api import runner
from textwrap import dedent
stage = 1

for type in ('vms', 'hosts', 'pools'):
    with open(f'src/{type}.xml','w') as stream:
        stream.write(dedent(f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE {type} [
        <!ENTITY json SYSTEM "{type}.json">
        ]>
        <{type}>&json;</{type}>""").strip())