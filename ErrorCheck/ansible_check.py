
import csv
import json
import pprint

def main():
    d = ansible()
    l = compare(d)
    f = assoc(l)
    with open('ans_missed.csv', 'w', newline='') as o:
        writer = csv.writer(o)
        for i in f:
            writer.writerow([i, f[i]])

def ansible():
    with open('../Sources/ansible.txt', 'r') as stream:
        first = True
        hostdict = {}
        for line in stream:
            if '=>' in line:
                hostname = line.split('|')[0].strip('\t \n').replace('.internal', '')
                if not first:
                    jsonobj = json.loads(string)
                    for ip in jsonobj['ansible_facts']['ansible_all_ipv4_addresses']:
                        hostdict[ip] = hostname
                string = '{\n'
                first = False
            else:
                string += line
    return hostdict

def compare(hostdict):
    with open('../Sources/active_ips.csv', 'r') as stream:
        iplist = []
        for row in csv.reader(stream):
            if row[1] == '192.168':
                if row[0] not in hostdict:
                    iplist.append(row[0])
    return iplist

def assoc(iplist):
    outdict = {}
    with open('../Sources/doc_domains.json') as stream:
        jsondata = json.load(stream)
        for d in jsondata:
            domain = jsondata[d]
            if 'ips' in domain:
                for ip in domain['ips']:
                    if ip in iplist:
                        outdict[ip] = d
            if 'internal' in domain:
                intdomain = domain['internal']
                for i in intdomain.keys():
                    intd = i
                if 'ips' in intdomain:
                    for ip in intdomain['ips']:
                        if ip in iplist:
                            outdict[ip] = intd
    return outdict
            

if __name__ == '__main__':
    main()