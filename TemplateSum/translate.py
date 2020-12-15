from bs4 import BeautifulSoup
import os

def main():
    for file in os.scandir('src'):
        translate(file)

def translate(f):
        with open(f, 'r') as stream:
            sourcename = f.name.replace('.psml', '')
            insoup = BeautifulSoup(stream, features='xml')
            outsoup = BeautifulSoup('', features='xml')
            root = outsoup.new_tag('document')
            root['level'] = 'portable'
            root['type'] = 'template'
            outsoup.append(root)
            section = outsoup.new_tag('section')
            section['id'] = 'main'
            root.append(section)
            for p in insoup.find_all('property'):
                with open('template.xml', 'r') as template:
                    tempsoup = BeautifulSoup(template, 'lxml')
                    frag = tempsoup.find('fragment')
                    frag['id'] = p['name']
                    propinfokey = propinfo[sourcename][p['name']]

                    tempsoup.find('heading', level='1').string = p['title']
                    for cell in tempsoup.find_all('cell'):
                        if cell.has_attr('role'):
                            role = cell['role']
                            if role == 'ptype':
                                if p.has_attr('datatype'):
                                    cell.string = p['datatype']
                                else:
                                    cell.string = 'string'
                            elif role == 'pval':
                                if p['name'] == 'template_version':
                                    cell.string = p['value']
                                elif p.has_attr('datatype'):
                                    cell.string = 'xref'
                                else:
                                    cell.string = propinfokey['example']
                            elif role == 'pname':
                                cell.string = p['name']
                            elif role == 'fid':
                                if 'fragment' in p.parent.name:
                                    cell.string = p.parent['id']
                                else:
                                    cell.string = 'None'
                            elif role == 'ftype':
                                cell.string = p.parent.name
                            elif role == 'sid':
                                if 'fragment' in p.parent.name:
                                    cell.string = p.parent.parent['id']
                                else:
                                    cell.string = 'None: metadata'
                            elif role == 'ctempver':
                                cell.string = insoup.find('property', title='Template version')['value']
                            elif role == 'otempver':
                                cell.string = propinfokey['otempver']
                    tempsoup.find('para').string = propinfokey['desc']             
                section.append(frag)
        with open('outgoing/' + f.name, 'w') as o:
            o.write(str(outsoup))


propinfo = {
    'host': {
        'template_version': {
            'desc': 'Document metadata property designed to support the calibration of evolving versions of the templates, document instances, Simple facet search and user interface and template documentation.',
            'otempver': '1.0'
        },
        'hostname': {
            'example': 'ps.allette.com.au',
            'desc': 'A domain name',
            'otempver': '1.0'
        },
        'primary': {
            'example': 'allette.com.au',
            'desc': 'The primary domain; the hostname without the subdomain',
            'otempver': '1.2'
        },
        'subdomain': {
            'example': 'ps',
            'desc': 'The subdomain; the hostname without the primary domain',
            'otempver': '1.3'
        },
        'adname': {
            'example': 'pageseeder.com.internal',
            'desc': 'The alternative name the domain has in Active Directory',
            'otempver': '1.3'
        },
        'source': {
            'example': 'DNSMadeEasy',
            'desc': 'Resource the document info came from',
            'otempver': '1.1'
        },
        'intip': {
            'example': '192.168.200.45',
            'desc': 'A private IP address',
            'otempver': '1.4'
        },
        'extip': {
            'example': '103.127.18.4',
            'desc': 'A public IP address',
            'otempver': '1.4'
        },
        'container': {
            'example': 'www-allette-com-au',
            'desc': 'Name of container associated with said domain (e.g. allette.com.au)',
            'otempver': '1.1'
        },
        'image': {
            'example': 'registry-gitlab.allette.com.au/pageseeder/psberlioz-simple:2020.11-1',
            'desc': 'ID of image associated with said domain (e.g. allette.com.au)',
            'otempver': '1.1'
        },
        'port': {
            'desc': 'xref to port which is open on said domain',
            'otempver': '1.0'
        }
    },
    'ip': {
        'template_version': {
            'desc': 'Document metadata property designed to support the calibration of evolving versions of the templates, document instances, Simple facet search and user interface and template documentation.',
            'otempver': '1.0'
        },
        'network': {
            'example': '192.168',
            'desc': 'The first two octets of the IP address (taken from 192.168.200.45)',
            'otempver': '1.0'
        },
        'subnet': {
            'example': '200',
            'desc': 'The third octet of the IP address; the subnet (taken from 192.168.200.45)',
            'otempver': '1.0'
        },
        'ip': {
            'example': '45',
            'desc': 'The last octet of the IP address (taken from 192.168.200.45)',
            'otempver': '1.0'
        },
        'port': {
            'desc': 'xref to port which is open on said ip',
            'otempver': '1.0'
        }
    },
    'port': {
        'template_version': {
            'desc': 'Document metadata property designed to support the calibration of evolving versions of the templates, document instances, Simple facet search and user interface and template documentation.',
            'otempver': '1.0'
        },
        'port': {
            'example': '80',
            'desc': 'Port number',
            'otempver': '1.0'
        },
        'service': {
            'example': 'http',
            'desc': 'service running on said port',
            'otempver': '1.0'
        }
    }
}

if __name__ == '__main__':
    main()

# frag = outsoup.new_tag('properties-fragment')
#             frag['id'] = id
#             section.append(frag)

#             title = outsoup.new_tag('property')
#             title['name'] = 'title'
#             title['title'] = 'Title'
#             title['value'] = p['title']
#             frag.append(title)
            
#             type = outsoup.new_tag('property')
#             type['name'] = 'type'
#             type['title'] = 'Type'
#             if id == 'template-version':
#                 type['value'] = 'Template version'
#             elif p.has_attr('value'):
#                 type['value'] = 'text'
#             elif p['datatype'] == 'xref':
#                 type['value'] = 'xref'
#             frag.append(type)

#             pfragtype = outsoup.new_tag('property')
#             pfragtype['name'] = 'fragmenttype'
#             pfragtype['title'] = 'Fragment Type'
#             pfragtype['value'] = p.parent.name
#             frag.append(pfragtype)

#             pfragid = outsoup.new_tag('property')
#             pfragid['name'] = 'fragmentid'
#             pfragid['title'] = 'Fragment ID'
#             if p.parent.name.endswith('fragment'):
#                 pfragid['value'] = p.parent['id']
#             else:
#                 pfragid['value'] = 'None'
#             frag.append(pfragid)

#             value = outsoup.new_tag('property')
#             value['name'] = 'value'
#             value['title'] = 'Value'
#             if p.has_attr('value'):
#                 value['value'] = '?'
#             elif p['datatype'] == 'xref':
#                 value['value'] = 'xref'
#             frag.append(value)