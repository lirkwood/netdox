from setuptools import setup, find_packages

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
    version = '0.0.0',
    url = 'https://netdox.allette.com.au/',
    download_url = 'https://gitlab.allette.com.au/allette/devops/network-documentation',
    packages = ['netdox', 'netdox.objs'] + [f'netdox.plugins.{pkg}' for pkg in find_packages(where = 'netdox/plugins')],
    package_data = {
        "": ["README.md"],
        "netdox": ["src/defaults/*/*"]
    },
    install_requires = [
        'beautifulsoup4',
        'lxml',
        'requests',
        'Pillow',
        'websockets',
        'boto3',
        'kubernetes',
        'pyppeteer',
        'diffimg',
        'pypsrp',
        'fortiosapi'
    ],
    entry_points = {'console_scripts': ['netdox=netdox.cli:parse_args']}
)