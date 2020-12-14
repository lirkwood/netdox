from bs4 import BeautifulSoup
import pprint
import csv

##########################################################################################################
# takes all domains and their associated records and compiles a list of all domains and their subdomains #
##########################################################################################################
def main():
    domains = open("../Sources/domains.xml", "r")  #for top level domains
    records = open("../Sources/records.xml", "r")  #for subdomains
    output = open("../sources/domains.csv", "w", newline='')
    writer = csv.writer(output)

    rsoup = BeautifulSoup(records, features='xml')
    dsoup = BeautifulSoup(domains, features='xml')

    type = rsoup.type   #grab all type tags
    value = rsoup.value #all subdomain url tags

    global dmndict
    global rcddict
    dmndict = {}
    rcddict = {}

    for domain in dsoup.find_all('data'):
        dmndict[domain.id.string.strip(' \n.')] = domain.find('name').string.strip(' \n.')    #skip dupes and make lists for subdomains
    
    count = 0
    for record in rsoup.find_all('data'):
        type = clean(record.type)
        value = clean(record.value)
        sourceid = clean(record.sourceId)
        name = clean(record.find('name'))
        if type == 'A': #for A records, build correct domain name and associate with IP
            ip = value
            if name:
                parent = dmndict[sourceid]
                domain = name + '.' + parent
            else:
                domain = dmndict[sourceid]
                
            domain = domain.replace('*.', '')
            domain = domain.replace('www.', '')
            count += 1
            if domain in rcddict:
                rcddict[domain].append(ip)
            else:
                rcddict[domain] = [ip]
    # print(count)

    count = 0
    for record in rsoup.find_all('data'):
        type = clean(record.type)
        if type == 'CNAME':
            count += 1
            cname(record)
    # print(count)

    for d in rcddict:
        for ip in rcddict[d]:
            writer.writerow(['DNSMadeEasy', d, ip])

def cname(record):
    global dmndict
    global rcddict

    sourceid = clean(record.sourceId)
    parent = dmndict[sourceid]
    alias = clean(record.find('name'))
    value = clean(record.value)
    if value:
        if value.endswith('.'):
            dest = value.strip('.')
        else:
            dest = value + '.' + parent
    else:
        dest = parent
    if alias:
        domain = alias + '.' + parent
    else:
        domain = parent
    domain = domain.replace('*.', '')
    domain = domain.replace('www.', '')
    if dest in rcddict:
        ips = list(rcddict[dest])
    else:
        ips = None

    if ips:
        for ip in ips:
            if domain in rcddict:
                rcddict[domain].append(ip)
            else:
                rcddict[domain] = [ip]
    
    
def clean(s):
    if len(s) > 0:
        s = s.string.strip(' \n')
        return s

if __name__ == '__main__':
    main()
