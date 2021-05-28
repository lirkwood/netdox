from docutils import nodes
from sphinx.builders import Builder
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxTranslator
from docutils.writers import Writer
from docutils.io import StringOutput
from urllib.parse import quote
from shutil import rmtree
from xml.sax.saxutils import escape
import os, re

from conf import project
project = project.lower()

def setup(app: Sphinx):
    entry_points = {
        'sphinx.builders': ['psml = psmlwriter.PSMLBuilder']
    }
    app.add_builder(PSMLBuilder)


class PSMLTranslator(SphinxTranslator):
    body: str = ''
    indent: int = 0
    heading_level: int = 0
    frag_count: int = 0
    textelems: list[str] = ['paragraph', 'title', 'item']
    xref_type = "none"
    docname = ''
    title = ''

    @property
    def in_textelem(self):
        for elem in self.textelems:
            if getattr(self, f'in_{elem}'):
                return True
        return False

    def depart_textelem(self):
        for elem in self.textelems:
            if getattr(self, f'in_{elem}'):
                getattr(self, f'depart_{elem}')(self)

    
    ############################
    # Element specific methods #
    ############################

    # Default behaviour
    def unknown_visit(self, node: nodes.Node) -> None:
        print(node.__dict__)
        raise NotImplementedError(f'Node {node.__class__.__name__} has not been implemented yet.')

    ## Structural elements ##

    # Document
    def visit_document(self, node: nodes.Node):
        self.body += '<document level="portable">'

        self.docname = os.path.basename(node['source'])
        self.body += f'<documentinfo><uri docid="_sphinx_{project}_{self.docname.split(".")[0]}" title="#_title_#" />'
        # make index a publication root
        if self.docname == 'index.rst':
            self.body += f'<publication id="_sphinx_{project}_root" type="default"/>'

        self.body += '</documentinfo><section id="body">'

    def depart_document(self, node: nodes.Node = None):
        self.body += '</fragment></section></document>'

    # Section
    def visit_section(self, node: nodes.Node = None) -> None:
        self.heading_level += 1
    
    def depart_section(self, node: nodes.Node = None) -> None:
        self.heading_level -= 1

    # Field List
    def visit_field_list(self, node: nodes.Node) -> None:
        raise nodes.SkipDeparture

    # Field
    def visit_field(self, node: nodes.Node = None) -> None:
        pass
    
    def depart_field(self, node: nodes.Node) -> None:
        self.depart_paragraph(node)

    # Field name
    def visit_field_name(self, node: nodes.Node) -> None:
        self.visit_paragraph(node)
        self.visit_strong(node)
    
    def depart_field_name(self, node: nodes.Node) -> None:
        self.body += ':'
        self.depart_strong(node)
        self.depart_paragraph(node)
        self.leaving_inline = False

    # Field body
    def visit_field_body(self, node: nodes.Node = None) -> None:
        self.indent += 1
    
    def depart_field_body(self, node: nodes.Node = None) -> None:
        self.indent -= 1

    ## Xrefs ##

    # Fragment/Xref target
    def visit_target(self, node: nodes.Node) -> None:
        if self.frag_count:
            self.body += '</fragment>'
        self.body += f'<fragment id="{node["refid"]}">'
        self.frag_count += 1
        raise nodes.SkipDeparture

    # Xref
    def visit_reference(self, node: nodes.Node) -> None:
        if node['internal']:
            if 'refuri' in node:
                xref_display = 'document'
                if '#' in node['refuri']:
                    document, refid = node['refuri'].split('#')
                else:
                    document, refid = node['refuri'], 'default'
            elif 'refid' in node:
                xref_display = 'document+fragment'
                document, refid = self.docname, node['refid']
            else:
                raise nodes.SkipNode

            docid = document.split('.')[0]
            if self.xref_type in ("embed", "transclude"):
                self.body += f'<blockxref frag="{refid}" display="{xref_display}" type="{self.xref_type}" docid="_sphinx_{project}_{docid}">'
            else:
                self.body += f'<xref frag="{refid}" display="{xref_display}" type="{self.xref_type}" docid="_sphinx_{project}_{docid}">'
    
    def depart_reference(self, node: nodes.Node = None) -> None:
        if self.xref_type in ("embed", "transclude"):
            self.body += '</blockxref>'
        else:
            self.body += '</xref>'

    ## Text elements ##

    # Paragraph
    def visit_paragraph(self, node: nodes.Node = None) -> None:
        if not self.in_textelem:
            if self.indent:
                self.body += f'<para indent="{self.indent}">'
            else:
                self.body += f'<para>'
    
    def depart_paragraph(self, node: nodes.Node = None) -> None:
        if self.in_paragraph:
            self.body += '</para>'

    @property
    def in_paragraph(self):
        paras = re.split(r'<para( indent="\d+")?>', self.body)
        if len(paras) > 1:
            if '</para>' not in paras[-1]:
                return True
        return False
    
    # Title
    def visit_title(self, node: nodes.Node) -> None:
        self.depart_paragraph(node)
        if not self.title:
            self.title = node.astext()
            self.body = re.sub(r'#_title_#', self.title, self.body)
        
        self.body += f'<heading level="{self.heading_level}">'
    
    def depart_title(self, node: nodes.Node) -> None:
        self.body += '</heading>'

    @property
    def in_title(self):
        headings = re.split(r'<heading( level="\d+")?>', self.body)
        if len(headings) > 1:
            if '</heading>' not in headings[-1]:
                return True
        return False

    # Text
    def visit_Text(self, node: nodes.Node) -> None:
        if self.in_textelem:
            self.body += escape(node.astext())
            # content = escape(node.astext())
            # if '\n' in content:
            #     for line in content.splitlines():
            #         self.body += (self.indent + line + '\n')
            # else:
            #     if self.in_inline:
            #         self.body += content
            #     elif self.leaving_inline:
            #         self.body += content
            #         self.leaving_inline = False
            #     else:
            #         # skip adding indent if text elem within other text elem
            #         self.body += (self.indent + content)
        else:
            self.visit_paragraph(node)
            self.visit_Text(node)
            self.depart_paragraph(node)
        
        raise nodes.SkipDeparture

    ## List-like ##

    # ToC
    def visit_compound(self, node: nodes.Node) -> None:
        self.xref_type = "embed"
    
    def depart_compound(self, node: nodes.Node) -> None:
        self.xref_type = "none"

    # Bullet list
    def visit_bullet_list(self, node: nodes.Node) -> None:
        if self.in_item:
            raise nodes.SkipNode
        elif self.in_textelem:
            self.depart_textelem()
        self.body += '<list>'
    
    def depart_bullet_list(self, node: nodes.Node = None) -> None:
        # if not self.in_textelem:
        self.body += '</list>'

    # Generic list item
    def visit_list_item(self, node: nodes.Node = None) -> None:
        self.body += '<item>'
    
    def depart_list_item(self, node: nodes.Node = None) -> None:
        self.body += '</item>'

    @property
    def in_item(self):
        items = re.split(r'<item>', self.body)
        if len(items) > 1:
            if '</item>' in items:
                return False
            else:
                return True

    # Definition list
    def visit_definition_list(self, node: nodes.Node = None) -> None:
        raise nodes.SkipDeparture

    # Definition list item
    def visit_definition_list_item(self, node: nodes.Node) -> None:
        raise nodes.SkipDeparture

    # Term to be defined
    def visit_term(self, node: nodes.Node = None) -> None:
        pass

    def depart_term(self, node: nodes.Node = None) -> None:
        self.body += '\n'
    
    # Definition
    def visit_definition(self, node: nodes.Node = None) -> None:
        self.indent += 1

    def depart_definition(self, node: nodes.Node = None) -> None:
        self.indent -= 1
        
    ## Emphasis/Inline ##

    # Bold
    def visit_strong(self, node: nodes.Node = None) -> None:
        self.body += '<bold>'
    
    def depart_strong(self, node: nodes.Node = None) -> None:
        self.body += '</bold>'
    
    # Italics
    def visit_emphasis(self, node: nodes.Node = None) -> None:
        self.body += '<italic>'
    
    def depart_emphasis(self, node: nodes.Node = None) -> None:
        self.body += '</italic>'
    
    # Code/Monospace
    def visit_literal(self, node: nodes.Node = None) -> None:
        self.body += '<monospace>'
    
    def depart_literal(self, node: nodes.Node = None) -> None:
        self.body += '</monospace>'

    # Inline
    def visit_inline(self, node: nodes.Node = None) -> None:
        pass
    
    def depart_inline(self, node: nodes.Node = None) -> None:
        pass

    ## Functions descriptions ##

    # Function description container
    def visit_desc(self, node: nodes.Node) -> None:
        self.visit_paragraph(node)
    
    def depart_desc(self, node: nodes.Node) -> None:
        self.depart_paragraph(node)

    # Function name
    def visit_desc_name(self, node: nodes.Node) -> None:
        raise nodes.SkipDeparture

    # Function name decoration
    def visit_desc_addname(self, node: nodes.Node) -> None:
        raise nodes.SkipDeparture
    
    # Function annotation
    def visit_desc_annotation(self, node: nodes.Node) -> None:
        raise nodes.SkipDeparture

    # Signature container
    def visit_desc_signature(self, node: nodes.Node) -> None:
        self.visit_literal(node)
    
    def depart_desc_signature(self, node: nodes.Node) -> None:
        self.depart_literal(node)

    # Parameter list
    def visit_desc_parameterlist(self, node: nodes.Node = None) -> None:
        self.body += '('
    
    def depart_desc_parameterlist(self, node: nodes.Node = None) -> None:
        self.body += '):'

    # Param list item
    def visit_desc_parameter(self, node: nodes.Node = None) -> None:
        # add comma before every param except for first
        if not self.body[-1] == '(':
            self.body += ', '
        raise nodes.SkipDeparture

    # Return values
    def visit_desc_returns(self, node: nodes.Node = None) -> None:
        self.body += ' -> '
        raise nodes.SkipDeparture

    # Docstring content
    def visit_desc_content(self, node: nodes.Node = None) -> None:
        self.depart_paragraph(node)
        self.indent += 1

    def depart_desc_content(self, node: nodes.Node = None) -> None:
        self.indent -= 1

    ## Other ##

    # Index
    def visit_index(self, node: nodes.Node) -> None:
        raise nodes.SkipDeparture
    


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

    def get_target_uri(self, docname: str, _=None) -> str:
        return quote(docname) + '.psml'

    def prepare_writing(self, _) -> None:
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