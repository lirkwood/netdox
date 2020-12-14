import json
import pprint

def clean():
    with open('../../Sources/ansible/ansible.txt', 'r') as stream:
        master = {}
        first = True
        for line in stream:
            if '=>' in line or line == '':
                if not first:
                    master[host] = json.loads(string)
                host = line.split('|')[0].strip('\n \t')
                if host.endswith('.internal'):
                    host = host.replace('.internal', '')
                first = False
                string = '{'
            else:
                string += line
    return master

def dictfromlist(obj):
    temp = {}
    if type(obj) == dict:
        for key in obj:
            temp[key] = dictfromlist(obj[key])
    elif type(obj) == list:
        count = 0
        for i in range(len(obj)):
            temp[count] = dictfromlist(obj[i])
            count += 1
    else:
        temp = obj
    
    return temp

def main():
    master = clean()
    master = dictfromlist(master)
    with open('../../sources/ansible/ansible.json', 'w') as o:
        o.write(json.dumps(master, indent=4))

    with open('../../sources/ansible/report_json.xml', 'w') as o:
        o.write('<data>')
        o.write(json.dumps(master, indent=4))
        o.write('</data>')

    for host in master:
        master[host]['ansible_facts'].pop('ansible_date_time')
        master[host]['ansible_facts'].pop('ansible_mounts')
        docid = '_nd_' + host.replace('.', '_')
        json_docid = docid + '_json'
        with open('json/{0}.psml'.format(json_docid), 'w') as o:
            o.write('<document level="portable"><documentinfo><uri docid="{0}"/></documentinfo><section id="main"><fragment id="json"><preformat role="lang-json">'.format(json_docid))
            o.write(json.dumps(master[host], indent=4))
            o.write('</preformat></fragment></section></document>')
        with open("outgoing/{0};json;.psml".format(docid), 'w') as o:
            o.write('<fragment id="json"><blockxref type="transclude" frag="default" docid="{0}"/></fragment>'.format(json_docid))

if __name__ == '__main__':
    main()