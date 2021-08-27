# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import re
import os
import sys
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../netdox'))
sys.path.insert(0, os.path.abspath('../netdox/plugins'))
sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'Netdox'
copyright = '2021, Linus Kirkwood'
author = 'Linus Kirkwood'

# The full version, including alpha/beta/rc tags
release = '0.0.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    # "sphinx.ext.linkcode",
    "psmlwriter"
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['../_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['../_static']


# -- Autodoc configuration ---------------------------------------------------

autodoc_member_order = 'bysource'
add_module_names = False

# -- Linkcode configuration --------------------------------------------------

def linkcode_resolve(domain, info):
    if domain != 'py':
        return None
    if not info['module']:
        return None
    
    modulepath = info["module"].replace('.','/')
    
    if os.path.isfile(f'../netdox/{modulepath}.py'):
        path = f'../netdox/{modulepath}.py'
    elif os.path.isdir(f'../netdox/{modulepath}'):
        path = f'../netdox/{modulepath}/__init__.py'

    try:
        with open(path, 'r', encoding='utf-8') as stream:
            lines = stream.readlines()
            functionLine = None
            for lineNum in range(len(lines)):
                if re.search(rf'(def|class) {info["fullname"]}', lines[lineNum]):
                    functionLine = lineNum + 1
    except Exception as e:
        print('Linkcode threw: ')
        print(e)
        print(info)
        functionLine = None

    base = 'gitlab.allette.com.au/allette/devops/network-documentation/-/tree/master/netdox'
    if functionLine:
        return f'https://{base}/{info["module"]}.py#L{functionLine}'
    else:
        return f'https://{base}/{info["module"]}.py'
