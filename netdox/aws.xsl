<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

  <xsl:output method="xml" indent="yes" />

  <!-- default template -->
  <xsl:template match="/">
      <xsl:variable name="aws" select="json-to-xml(aws)" />
      <xsl:apply-templates select="$aws//xpf:array/xpf:map" />
  </xsl:template>

  <xsl:template match="xpf:array/xpf:map">
    <xsl:result-document href="/opt/app/out/aws/{xpf:string[@key = 'InstanceId']}.psml" method="xml" indent="yes" omit-xml-declaration="yes">
      <document type="ec2" level="portable">
        <documentinfo>
          <uri title="{xpf:string[@key='Name']}" docid="_nd_{xpf:string[@key = 'InstanceId']}" />
        </documentinfo>

        <metadata>
          <properties>
            <property name="template-version"     title="Template version"   value="1.0" />
          </properties>
        </metadata>

        <section id="details" title="details">
          <properties-fragment id="core">
            <property name="name" title="Name" value="{xpf:string[@key='Name']}"/>
            <property name="environemnt" title="Environment" value="{xpf:string[@key='Environment']}"/>
            <property name="instanceId" title="Instance Id" value="{xpf:string[@key='InstanceId']}"/>
            <property name="instanceType" title="Instance Type" value="{xpf:string[@key='InstanceType']}"/>
            <property name="availabilityZone" title="Availability Zone" value="{xpf:string[@key='AvailabilityZone']}"/>
            <property name="ipv4" title="Public IP" value="{xpf:string[@key='PublicIpAddress']}"/>
            <property name="ipv4" title="Private IP" datatype="xref">
              <xref frag="default" docid="_nd_{translate(xpf:string[@key='PrivateIpAddress'],'.','_')}" reversetitle="AWS EC2 instance on this IP"/>
            </property>
          </properties-fragment>
        </section>
      </document>
    </xsl:result-document>
  </xsl:template>
</xsl:stylesheet>
