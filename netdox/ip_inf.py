import json
import iptools, nat_inf, utils

@utils.critical
def main(ipdict, ptr):
    tmp = {}
    subnets = set()
    for ip in ipdict:
        _ip = iptools.ipv4(ip)
        if _ip.valid:
            if (not _ip.public) or _ip.in_subnet('103.127.18.0/24') or _ip.in_subnet('119.63.219.195/26'):
                subnet = iptools.subnet(f'{_ip.ipv4}/24')
                if subnet not in subnets:
                    subnets.add(subnet)
                    for sibling in subnet.iterate():
                        if sibling not in ipdict:
                            tmp[sibling] = {'source': 'Generated'}
    ipdict = tmp | ipdict   #populate ipdict with unused private ips

    for ip in ipdict:
        _ip = iptools.ipv4(ip)
        ipnat = nat_inf.lookup(ip)
        if ipnat:
            ipdict[ip]['nat'] = ipnat
        if ip in ptr:
            ipdict[ip]['ptr'] = ptr[ip]
        ipdict[ip]['subnet'] = _ip.subnet
        ipdict[ip]['network'] = f'{_ip.octets[0]}.{_ip.octets[1]}.0.0/16'
        ipdict[ip]['for-search'] = f"{ip.split('.')[2]}, {'.'.join(ip.split('.')[2:4])}"
    
    with open('src/ips.json','w') as output:
        output.write(json.dumps(ipdict, indent=2))