from docutils import nodes
from sphinx.builders import Builder
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxTranslator
from docutils.writers import Writer
from docutils.io import FileOutput
from urllib.parse import quote
from shutil import rmtree
from xml.sax.saxutils import escape
import os, re

from conf import project
project = project.lower()

# re pattern of chars not allowed in fragment ids
FRAGMENT_ID_INVALID = re.compile(r'[^a-zA-Z0-9_=,&\.-]{1}')

def setup(app: Sphinx):
    entry_points = {
        'sphinx.builders': ['psml = psmlwriter.PSMLBuilder']
    }
    app.add_builder(PSMLBuilder)


class PSMLTranslator(SphinxTranslator):
    body: str = ''
    toc: str = ''
    indent: int = 0
    heading_level: int = 0
    frag_count: int = 0
    """Counter for generating unique fragment ids"""
    fragment: str = None
    section: bool = False
    textelems: list[str] = ['para', 'heading', 'item']
    xref_type: str = "none"
    docname: str = ''
    title: str = ''

    ##################################
    # Functions for finding position #
    ##################################

    def in_tag(self, tag: str):
        if len(re.findall(rf'<{tag}.*?>', self.body)) > len(re.findall(rf'</{tag}>', self.body)):
            return True
        return False

    @property
    def in_textelem(self):
        for elem in self.textelems:
            if self.in_tag(elem):
                return True
        return False

    def depart_textelem(self):
        for elem in self.textelems:
            if self.in_tag(elem):
                self.body += f'</{elem}>'

    def enter_section(self, id: str, title: str = None):
        """
        Starts a new section element. Exits current section if necessary.
        """
        if self.section:
            self.exit_section()
        titleattr = f'title="{title}"' if title else ''
        self.body += f'<section id="{id}" {titleattr}>'
        self.section = True

    def exit_section(self):
        """
        Exits the current section element, if any.
        """
        if self.section:
            self.body += '</section>'
        self.section = False

    def enter_frag(self, type: str, id: str = None):
        """
        Starts a new fragment element. Exits current fragment if necessary.
        """
        assert self.section, 'Cannot start fragment outside of section.'
        if self.fragment:
            self.exit_frag()
        if id:
            id = re.sub(FRAGMENT_ID_INVALID, "_", id)
        else:
            self.frag_count += 1
            id = str(self.frag_count)
        
        self.body += f'<{type} id="{id}">'
        self.fragment = type

    def exit_frag(self):
        """
        Exits the current fragment element, if any.
        """
        if self.fragment:
            self.body += f'</{self.fragment}>'
            self.fragment = None

    
    ############################
    # Element specific methods #
    ############################

    # Default behaviour
    def unknown_visit(self, node: nodes.Node) -> None:
        raise NotImplementedError(f'Node {node.__class__.__name__} has not been implemented yet.')

    ## Structural elements ##

    # Document
    def visit_document(self, node: nodes.Node):
        self.docname = os.path.basename(node['source'])
        if self.docname == 'index.rst':
            root = True
        else:
            root = False

        self.body += f'<document level="portable" type="{"references" if root else "default"}">'
        self.body += f'<documentinfo><uri title="#_title_#"/>'

        if root: self.body += f'<publication id="_sphinx_{project}_root"/>'

        self.body += '</documentinfo>'
        self.enter_section('body')

    def depart_document(self, node: nodes.Node = None):
        self.exit_frag()
        self.exit_section()
        self.body += '</document>'

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
        if 'refid' in node:
            id = node["refid"]
        elif 'ismod' in node and node['ismod']:
            id = node["ids"][0].split('-')[-1]
        else:
            raise nodes.SkipNode

        if self.fragment:
            self.exit_frag()
        self.enter_frag('fragment', id)
        raise nodes.SkipDeparture

    # Xref
    def visit_reference(self, node: nodes.Node) -> None:
        if 'internal' in node and node['internal']:
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
            
            refid = re.sub(FRAGMENT_ID_INVALID, '_', refid)

            if self.xref_type in ("embed", "transclude"):
                self.body += f'<blockxref frag="{refid}" display="{xref_display}" type="{self.xref_type}" href="{document}">'
            else:
                self.body += f'<xref frag="{refid}" display="{xref_display}" type="{self.xref_type}" href="{document}">'

            text = node.children[0].rawsource
            self.body += text
            self.depart_reference()
            raise nodes.SkipNode
        else:
            if 'name' in node:
                text = node['name']
            else:
                text = ' [source]'
            self.body += f'<link href="{node["refuri"]}">{text}</link>'
            raise nodes.SkipNode
    
    def depart_reference(self, node: nodes.Node = None) -> None:
        if self.xref_type in ("embed", "transclude"):
            self.body += '</blockxref>'
        else:
            self.body += '</xref>'

    ## Text elements ##

    # Paragraph
    def visit_paragraph(self, node: nodes.Node = None) -> None:
        if not self.fragment:
            self.enter_frag('fragment', self.frag_count)
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
        return self.in_tag('para')
    
    # Title
    def visit_title(self, node: nodes.Node) -> None:
        if self.in_textelem:
            self.depart_textelem()
        if not self.fragment:
            self.enter_frag('fragment')
        if not self.title:
            self.title = node.astext()
            self.body = re.sub(r'#_title_#', self.title, self.body)
        assert len(node.children) <= 1, 'Title element contains >1 children'
        self.body += f'<heading level="{self.heading_level}">'
    
    def depart_title(self, node: nodes.Node) -> None:
        self.body += '</heading>'

    # Text
    def visit_Text(self, node: nodes.Node) -> None:
        if self.in_textelem:
            self.body += escape(node.astext())
        else:
            self.visit_paragraph(node)
            self.visit_Text(node)
            self.depart_paragraph(node)
        
        raise nodes.SkipDeparture

    ## List-like ##

    # ToC
    def visit_compound(self, node: nodes.Node) -> None:
        self.xref_type = "embed"
        if self.fragment:
            self.exit_frag()
        self.enter_section('toc')
        self.enter_frag('fragment', 'toc')
    
    def depart_compound(self, node: nodes.Node) -> None:
        self.exit_frag()
        self.xref_type = "none"

    @property
    def in_toc(self):
        return self.body.startswith('<toc/>')

    # Bullet list
    def visit_bullet_list(self, node: nodes.Node) -> None:
        if self.in_bullet_list:
            raise nodes.SkipNode
        elif self.in_textelem:
            self.depart_textelem()
        self.body += '<list>'
    
    def depart_bullet_list(self, node: nodes.Node = None) -> None:
        self.body += '</list>'

    @property
    def in_bullet_list(self):
        return self.in_tag('list')

    # Generic list item
    def visit_list_item(self, node: nodes.Node = None) -> None:
        self.body += '<item>'
    
    def depart_list_item(self, node: nodes.Node = None) -> None:
        self.body += '</item>'

    @property
    def in_list_item(self):
        return self.in_tag('item')

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

    # Block quote
    def visit_block_quote(self, node: nodes.Node) -> None:
        if self.in_textelem:
            self.depart_textelem()
        self.indent += 1
        self.visit_paragraph()

    
    def depart_block_quote(self, node: nodes.Node) -> None:
        self.indent -= 1
        self.depart_paragraph()

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
        self.body += '<br/>'
    
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
        self.outdir = self.app.outdir

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        outpath = os.path.join(self.outdir, docname)
        if os.path.dirname(outpath) and not os.path.exists(os.path.dirname(outpath)):
            os.makedirs(os.path.dirname(outpath))
        dest = FileOutput(destination_path = os.path.join(self.outdir, f'{docname}.psml'), encoding = 'utf-8')
        self.docwriter.write(doctree, dest)


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