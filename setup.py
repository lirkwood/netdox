from setuptools import setup, find_namespace_packages

def readme() -> str:
    with open('README.md', 'r') as stream:
        return stream.read()

setup(
    name = 'netdox',
    description = 'Network documentation generator for use with PageSeeder.',
    long_description = readme(),
    long_description_content_type = 'text/markdown',
    author = 'Linus Kirkwood',
    author_email = 'linuskirkwood@gmail.com',
    version = '1.5.0',
    url = 'https://netdox.allette.com.au/',
    download_url = 'https://gitlab.allette.com.au/allette/devops/network-documentation',
    packages = find_namespace_packages(where = 'src'),
    package_dir = {"": "src"},
    package_data = {
        "": ["README.md"],
        "netdox": [
            "src/psml.xsd",
            "src/defaults/*",
            "src/templates/*",
            "src/templates/*/*",
        ],
        "netdox.plugins.screenshots": [
            "placeholder.jpg"
        ],
        "netdox.plugins.plantuml" : [
            "failed.svg"
        ]
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
    install_requires = [
        'beautifulsoup4',       # core
        'lxml',                 # core
        'requests',             # core
        'tldextract',           # core
        'websockets',           # xenorchestra
        'boto3',                # aws
        'kubernetes>=22.6.0',   # k8s
        'pyppeteer',            # screenshots, pfSense
        'diffimg',              # screenshots
        'pypsrp',               # activedirectory
        'fortiosapi',           # fortigate
        'pysnmp',               # snmp
        'plantuml'              # plantuml
    ],
    entry_points = {'console_scripts': ['netdox=netdox.cli:parse_args']}
)