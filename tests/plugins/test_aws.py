from datetime import datetime

from bs4 import BeautifulSoup
from netdox.plugins import aws
from netdox import Network
from pytest import fixture

@fixture
def period() -> aws.AWSTimePeriod:
    return aws.AWSTimePeriod(
        datetime(1999, 1, 1, 0, 0, 0, 0), datetime(1999, 1, 1, 1, 0, 0, 0))

class TestAWSTimePeriod:

    def test_from_str(self, period: aws.AWSTimePeriod):
        assert aws.AWSTimePeriod.from_str(period.to_str()) == period


class TestEC2Instance:
    ...

    # TODO reactivate with safe node-aws example
    # def test_from_psml(self):
    #     with open('resources/node-aws.psml', 'r') as stream:
    #         soup = BeautifulSoup(stream.read(), 'xml')
    #     node = aws.EC2Instance.from_psml(Network(), soup)

    #     assert isinstance(node, aws.EC2Instance)
    #     assert node.name == 'prod.01.www.oxforddigital.com.au'
    #     assert node.identity == '10.0.0.120'
    #     assert node.type == aws.EC2Instance.type

    #     assert node.id == 'i-04d9707795d642721'
    #     assert node.mac == '06:27:07:95:a9:f2'
    #     assert node.instance_type == 'c4.2xlarge'
    #     assert node.monitoring == 'disabled'
    #     assert node.region == 'ap-southeast-2b'
    #     assert node.key_pair == 'obook1'
    #     assert node.state == 'running'