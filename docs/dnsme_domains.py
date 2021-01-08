from bs4 import BeautifulSoup
import json
import csv

##########################################################################################################
# takes all domains and their associated records and compiles a list of all domains and their subdomains #
##########################################################################################################
def main():
    cnames = {}
    with open('../Sources/cnames.json', 'r') as stream:
        cnames = json.load(stream)
    with open("../Sources/domains.xml", "r") as domains:
        with open("../Sources/records.xml", "r") as records:
            with open("../sources/domains.csv", "a", newline='') as output:
                writer = csv.writer(output)

                rsoup = BeautifulSoup(records, features='xml')
                dsoup = BeautifulSoup(domains, features='xml')

                type = rsoup.type   #grab all type tags
                value = rsoup.value #all subdomain url tags

                dmndict = {}
                rcddict = {}

                for domain in dsoup.find_all('data'):
                    dmndict[domain.id.string] = domain.find('name').string    #skip dupes and make lists for subdomains
                
                for record in rsoup.find_all('data'):
                    type = record.type.string
                    value = record.value.string
                    sourceid = record.sourceId.string
                    parent = dmndict[sourceid]
                    name = record.find('name').string
                    if type == 'A':
                        ip = value
                        if name:
                            domain = name + '.' + parent
                        else:
                            domain = dmndict[sourceid]
                        
                        domain = domain.replace('*.', '')
                        domain = domain.replace('www.', '')
                        if domain in rcddict:
                            rcddict[domain].append(ip)
                        else:
                            rcddict[domain] = [ip]
                    elif type == 'CNAME':
                        if value and value.endswith('.'):
                            dest = value.strip('.')
                        else:
                            dest = dmndict[sourceid]
                            if value:
                                dest = value +'.'+ dest

                        if dest not in cnames:
                            cnames[dest] = []
                        cnames[dest].append(name +'.'+ parent)

                for d in rcddict:
                    for ip in rcddict[d]:
                        writer.writerow(['DNSMadeEasy', d, ip])
    with open('../Sources/cnames.json', 'w') as stream:
        for i in cnames:
            cnames[i] = list(dict.fromkeys(cnames[i]))
        stream.write(json.dumps(cnames, indent=4))
             
if __name__ == '__main__':
    main()
