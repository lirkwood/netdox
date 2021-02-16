import sys, subprocess, json
import iptools

authstream = open('../src/authentication.json','r')
auth = json.load(authstream)['XenOrchestra']
args = {
    'register': ['xo-cli', '--register', 'https://xo.allette.com.au', auth['Username'], auth['Password']],
    'pools': ['xo-cli', '--list-objects', '--name_label', '--name_description', '--uuid', '--master', 'type=pool'],
    'hosts': ['xo-cli', '--list-objects', '--name_label', '--name_description', '--uuid', '--hostname', '--address', '--CPUs', '--$pool', '--power_state', 'type=host'],
    'vms': ['xo-cli', '--list-objects', '--name_label', '--name_description', '--uuid', '--addresses', '--os_version', '--$container', '--$pool', '--power_state', 'type=VM'],
    'aws': ['/usr/local/bin/aws','ec2','describe-instances','--profile','oup','--output','json','--query','Reservations[*].Instances[*].{Name:Tags[?Key==`Name`]|[0].Value,Environment:Tags[?Key==`environment`]|[0].Value,InstanceId:InstanceId,InstanceType:InstanceType,AvailabilityZone:Placement.AvailabilityZone,PrivateIpAddress:PrivateIpAddress,PublicIpAddress:PublicIpAddress}']
}
pools = {}
controllers = set()
hosts = {}

def main():
    subprocess.run(args['register'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for type in ('pools', 'hosts', 'vms'): #temporarily removed 'aws'
        with open(f'../src/{type}.json', 'w+') as stream:
            content = subprocess.run(args[type], stdout=subprocess.PIPE)
            jsondata = json.loads(content.stdout)

            if type == 'pools':
                for pool in jsondata:
                    pools[pool['uuid']] = []
                    controllers.add(pool['master'])

            elif type == 'hosts':
                for host in jsondata:
                    if host['uuid'] not in controllers:
                        pools[host['$pool']].append(host['uuid'])
                    try:
                        ipv4 = iptools.parsed_ip(host['address'])
                        host['subnet'] = ipv4.subnet
                    except:
                        print('Failed to allocate a subnet to IPv4 address: '+ ipv4.ipv4, file=sys.stderr)

            elif type == 'vms':
                for vm in jsondata:
                    if vm['$container'] not in hosts:
                        hosts[vm['$container']] = []
                    hosts[vm['$container']].append(vm['uuid'])
                    try:
                        ipv4 = iptools.parsed_ip(vm['addresses']['0/ipv4/0'])
                        vm['subnet'] = ipv4.subnet
                    except:
                        print(f'VM {vm["name_label"]} has no ipv4.', file=sys.stderr)

            stream.write(json.dumps(jsondata, indent=2))

    with open('../src/roles.json', 'w') as stream:
        stream.write(json.dumps(pools, indent=4))

    with open('../src/residents.json', 'w') as stream:
        stream.write(json.dumps(hosts, indent=4))