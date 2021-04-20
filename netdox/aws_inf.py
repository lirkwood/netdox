import subprocess, utils

query = {
    "Name": "Tags[?Key=='Name']|[0].Value",
    "Environment": "Tags[?Key==`environment`]|[0].Value",
    "InstanceId": "InstanceId",
    "InstanceType": "InstanceType",
    "AvailabilityZone": "Placement.AvailabilityZone",
    "PrivateIpAddress": "PrivateIpAddress",
    "PublicIpAddress": "PublicIpAddress"
}

@utils.critical
def main():
    response = subprocess.check_output(['aws', 'ec2', 'describe-instances', '--query', 
    f"Reservations[*].Instances[*].{JMESPath_dict(query)}"])
    
    with open('src/aws.json', 'w') as stream:
        stream.write(str(response, encoding='utf-8'))
    
def JMESPath_dict(dictionary):
    """
    Encodes some JSON object as a JMSEPath query where values are JMESPath selectors to desired value
    """
    if isinstance(dictionary, dict):
        outstring = '{'
        for key in dictionary:
            if outstring != '{':
                outstring += ','
            outstring += f'{key}:{dictionary[key]}'
        outstring += '}'
        
        return outstring
    else:
        raise TypeError(f'[ERROR][aws_inf.py] Object to be encoded must be dictionary, not {type(dictionary)}')


if __name__ == '__main__':
    main()