from bs4 import BeautifulSoup
import csv

# def main():
#     output = open('../Sources/domains.csv', 'a', newline='')
#     writer = csv.writer(output)

#     stream = open('../Sources/ad.xml', 'r')
#     soup = BeautifulSoup(stream, 'lxml')

#     dict = {}
#     records = soup.find_all('record')
#     for record in records:
#         hostname = record.hostname.string
#         network = record.network.string
#         subnet = record.subnet.string
#         addr = record.addr.string

#         if '*' not in hostname:
#             hostname = hostname.replace('www.', '')
#             dict[hostname] = network +'.'+ subnet +'.'+ addr
#     #####################################################
    
#     for k in dict:
#         writer.writerow(['Active Directory', k, dict[k]])
        
def main():
    output = open('../Sources/domains.csv', 'w', newline='')
    writer = csv.writer(output)

    stream = open('../Sources/ad.xml', 'r')
    soup = BeautifulSoup(stream, 'lxml')

    outlist = []
    records = soup.find_all('record')
    for record in records:
        hostname = record.hostname.string
        network = record.network.string
        subnet = record.subnet.string
        addr = record.addr.string

        hostname = hostname.replace('www.', '')
        hostname = hostname.replace('*.', '')
        ip = network +'.'+ subnet +'.'+ addr
        outlist.append(['Active Directory', hostname, ip]) 
    #####################################################
    
    for i in outlist:
        writer.writerow(i)
    


if __name__ == '__main__':
    main()
