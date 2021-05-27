from typing import Set
from docutils import nodes
from sphinx.builders import Builder
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxTranslator
from docutils.writers import Writer
from docutils.io import StringOutput
from urllib.parse import quote
from shutil import rmtree
from xml.sax.saxutils import escape

import re, os

def setup(app: Sphinx):
    entry_points = {
        'sphinx.builders': ['psml = psmlwriter.Builder']
    }
    app.add_builder(PSMLBuilder)



class PSMLTranslator(SphinxTranslator):
    body = ''
    heading_level = 1
    section_count = 0
    def __init__(self, document: nodes.document, builder: "Builder") -> None:
        super().__init__(document, builder)

    def unknown_visit(self, node: nodes.Node) -> None:
        self.body += f'<untranslated:{node.__class__.__name__}>'

    def unknown_departure(self, node: nodes.Node) -> None:
        self.body += f'</untranslated:{node.__class__.__name__}>'
    
    ## Element specific methods

    # Document

    def visit_document(self, node: nodes.Node):
        self.body += r'<document level="portable">'

    def depart_document(self, node: nodes.Node):
        self.body += r'</document>'

    # Paragraph

    def visit_paragraph(self, node: nodes.Node) -> None:
        self.body += r'<para>'
    
    def depart_paragraph(self, node: nodes.Node) -> None:
        self.body += r'</para>'

    # Text
    
    def visit_Text(self, node: nodes.Node) -> None:
        self.body += escape(node.astext())
    
    def depart_Text(self, node: nodes.Node) -> None:
        pass

    # Title

    def visit_title(self, node: nodes.Node) -> None:
        self.body += f'<heading level="{self.heading_level}">'
        self.body += node.astext()
        self.heading_level += 1
    
    def depart_title(self, node: nodes.Node) -> None:
        self.body += '</heading>'
        self.heading_level -= 1

    # Section
    
    def visit_section(self, node: nodes.Node) -> None:
        self.body += f'<section id="{self.section_count}">'
        self.section_count += 1
    
    def depart_section(self, node: nodes.Node) -> None:
        self.body += '</section>'


class PSMLBuilder(Builder):
    """
    Builds PSML documents
    """
    name: str = 'psml'
    format: str = 'psml'
    epilog: str = 'PSML written to %(outdir)s for project %(project)s.'
    supported_image_types: list[str] = []
    default_translator_class = PSMLTranslator

    def __init__(self, app: Sphinx):
        super().__init__(app)
        self.app: Sphinx = app

    def get_target_uri(self, docname: str, typ: str=None) -> str:
        return quote(docname) + '.psml'

    def prepare_writing(self, docnames: set[str]) -> None:
        self.docwriter = PSMLWriter(self)
        self.outdir = os.path.join(self.app.outdir, 'psml')
        if os.path.exists(self.outdir):
            rmtree(self.outdir)
        os.mkdir(self.outdir)

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        dest = StringOutput(encoding='utf-8')
        doc = self.docwriter.write(doctree, dest)
        with open(os.path.join(self.outdir, f'{docname}.psml'), 'w', encoding='utf-8') as stream:
            stream.write(str(doc, encoding='utf-8'))


class PSMLWriter(Writer):
    def __init__(self, builder: PSMLBuilder) -> None:
        super().__init__()
        self.builder = builder
    
    def translate(self) -> None:
        self.visitor = self.builder.create_translator(self.document, self.builder)
        self.document.walkabout(self.visitor)
        self.output = self.visitor.body
        

elementMap = {
    'document': '<document>'
}