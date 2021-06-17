<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

  <xsl:output method="xml" indent="yes" />

  <!-- default template -->
  <xsl:template match="/">
      <xsl:variable name="aws" select="json-to-xml(aws)" />
      <xsl:apply-templates select="$aws/xpf:map/xpf:array[@key = 'Reservations']/xpf:map/xpf:array[@key = 'Instances']/xpf:map" />
  </xsl:template>

  <xsl:template match="xpf:array[@key = 'Instances']/xpf:map">
    <xsl:result-document href="out/aws/{xpf:string[@key = 'InstanceId']}.psml" method="xml" indent="yes" omit-xml-declaration="yes">
      <document type="aws_ec2" level="portable">
        <documentinfo>
          <uri title="{xpf:string[@key='KeyName']}" docid="_nd_{xpf:string[@key = 'InstanceId']}" />
        </documentinfo>

        <metadata>
          <properties>
            <property name="template-version"     title="Template version"   value="1.1" />
          </properties>
        </metadata>

        <section id="details" title="details">
          <properties-fragment id="info">
            <property name="name" title="Name" value="{xpf:string[@key='KeyName']}"/>
            <property name="environment" title="Environment" value="{xpf:array[@key='Tags']/xpf:map/xpf:string[preceding-sibling::*[. = 'environment']]}"/>
            <property name="instanceId" title="Instance Id" value="{xpf:string[@key='InstanceId']}"/>
            <property name="instanceType" title="Instance Type" value="{xpf:string[@key='InstanceType']}"/>
            <property name="monitoring" title="Monitoring" value="{xpf:map[@key='Monitoring']/xpf:string}" />
            <property name="state" title="State" value="{xpf:map[@key='State']/xpf:string}" />
            <property name="availabilityZone" title="Availability Zone" value="{xpf:map[@key = 'Placement']/xpf:string[@key='AvailabilityZone']}"/>
          </properties-fragment>
          <properties-fragment id="ips">
            <property name="ipv4" title="Public IP" datatype="xref">
              <xref frag="default" docid="_nd_{translate(xpf:string[@key='PublicIpAddress'],'.','_')}" reversetitle="AWS EC2 instance on this IP"/>
            </property>
            <property name="ipv4" title="Private IP" datatype="xref">
              <xref frag="default" docid="_nd_{translate(xpf:string[@key='PrivateIpAddress'],'.','_')}" reversetitle="AWS EC2 instance on this IP"/>
            </property>
          </properties-fragment>
          <properties-fragment id="domains">
            <property name="domain" title="Public Domain" value="{xpf:string[@key='PublicDnsName']}" />
            <property name="domain" title="Private Domain" value="{xpf:string[@key='PrivateDnsName']}" />
          </properties-fragment>
        </section>
      </document>
    </xsl:result-document>
  </xsl:template>
</xsl:stylesheet>
