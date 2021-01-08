import json
import csv

def main():
    stream = open('../Sources/ingress.json', 'r')
    jsondata = json.load(stream)
    domains = {}
    ip = {}
    for c in jsondata.keys():
        context = jsondata[c]
        domains[c] = []
        ip[c] = []

        for i in context['items'][0]['status']['loadBalancer']['ingress']:
            ip[c].append(i['ip'])

        for record in context['items']: #navigating to each record
            for i in record['spec']['rules']:   #get list of all domains
                domains[c].append(i['host'].replace('www.', ''))

            # domains[c] = list(dict.fromkeys(domains[c]))  #remove duplicates

    write(domains, ip)
        
def write(d, l):
    with open('../Sources/domains.csv', 'a', newline='') as stream:
        writer = csv.writer(stream)
        for c in d:
            context = d[c]
            for domain in context:
                hostname = domain
                hostname = hostname.replace('*.', '')
                hostname = hostname.replace('www.', '')
                outlist = ['Kubernetes', hostname]
                for ip in l[c]:
                    outlist.append(ip)
                writer.writerow(outlist[:2])

            

if __name__ == '__main__':
    main()
