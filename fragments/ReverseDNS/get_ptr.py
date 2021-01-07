from bs4 import BeautifulSoup
import pprint
import json
import os


def dnsme():
    dns_dict = {}
    with open('../Sources/records.xml', 'r') as stream:
        soup = BeautifulSoup(stream, 'lxml')
        ipbase = '103.127.18.'
        for record in soup.find_all('data'):
            if record.type.string == 'PTR':
                ip = ipbase + record.find('name').string
                domain = record.find('value').string.strip('.')
                if ip not in dns_dict:
                    dns_dict[ip] = []
                dns_dict[ip].append(domain)
    return dns_dict


def ad():
    ad_dict = {}
    for file in os.scandir('../Sources/records'):
        if 'ptr' in file.name:
            ipbase = '192.168.'
            subnet = file.name.split('-')[0] + '.'
            with open(file, 'r') as stream:
                jsondata = json.load(stream)
                for record in jsondata:
                    if record['RecordType'] == 'PTR':
                        ip = ipbase + subnet + record['HostName']
                        domain = record['RecordData']['CimInstanceProperties'].split('"')[1].strip('.')
                        if domain.endswith('.internal'):
                            domain = domain.replace('.internal', '')
                        elif domain.endswith('.interna'):
                            domain = domain.replace('.interna', '')

                        if ip not in ad_dict:
                            ad_dict[ip] = []
                        ad_dict[ip].append(domain)
    return ad_dict

def main():
    master = {}
    dns_dict = dnsme()
    ad_dict = ad()
    for i in dns_dict:
        master[i] = list(dict.fromkeys(dns_dict[i]))
    for i in ad_dict:
        master[i] = list(dict.fromkeys(ad_dict[i]))

    for ip in master:
        docid = '_nd_' + ip.replace('.', '_')
        soup = BeautifulSoup('', features='xml')
        frag = soup.new_tag('properties-fragment')
        soup.append(frag)
        for domain in master[ip]:
            prop = soup.new_tag('property')
            prop['name'] = 'ptr'
            prop['title'] = 'Reverse DNS Record'
            prop['datatype'] = 'xref'
            frag.append(prop)

            xref = soup.new_tag('xref')
            xref['frag'] = 'default'
            xref['docid'] = '_nd_' + domain.replace('.', '_')
            prop.append(xref)
        
        if not os.path.exists('reversedns/outgoing'):
            os.mkdir('reversedns/outgoing')
        with open('reversedns/outgoing/{0};reversedns;.psml'.format(docid), 'w') as o:
            o.write(soup.prettify())


if __name__ == '__main__':
    main()
