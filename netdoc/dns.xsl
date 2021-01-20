<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="dns" select="json-to-xml(dns)"/>
    <xsl:apply-templates select="$dns/xpf:map/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:variable name="name" select="@key"/>
    <xsl:result-document href="../outgoing/DNS/{translate($name,'.','_')}.psml" method="xml" indent="yes">
        <document type="dns" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="_nd_{translate($name,'.','_')}" title="dns: {$name}"><labels>show-reversexrefs</labels></uri>
            </documentinfo>

            <metadata>
                <properties>
                    <property name="template_version"     title="Template version"   value="3.3" />
                </properties>
            </metadata>

            <section id="title">
                <fragment id="title">
                    <heading level="1">dns: <xsl:value-of select="$name"/></heading>
                </fragment>
            </section>

            <section id="details" title="details">

                <properties-fragment id="host">
                    <property name="host"         title="Host"          value="{$name}" />
                    <property name="root"        title="Root"      value="{xpf:string[@key = 'root']}" />
                    <property name="source"        title="Source"      value="{xpf:string[@key = 'source']}" />
                </properties-fragment>

                <properties-fragment id="ipv4">
                <xsl:for-each select="xpf:map[@key = 'ips']/xpf:array[@key = 'private']">
                    <property name="ipv4" title="Private IP" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" />
                    </property>
                </xsl:for-each>
                <xsl:for-each select="xpf:map[@key = 'ips']/xpf:array[@key = 'public']">
                    <property name="ipv4" title="Public IP" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" />
                    </property>
                </xsl:for-each>
                </properties-fragment>
                
                <properties-fragment id="subnets">
                <xsl:for-each select="xpf:array[@key = 'subnets']/xpf:string">
                    <property name="subnet" title="Subnet" value="{.}" />
                </xsl:for-each>
                </properties-fragment>
            
                <properties-fragment id="aliases">
                <xsl:for-each select="xpf:array[@key = 'aliases']/xpf:string">
                    <property name="alias" title="Alias" value="{.}" />
                </xsl:for-each>
                </properties-fragment>
                
            </section>
            
            <section id="ansible" title="Ansible"/>
        
        </document>
    </xsl:result-document>
</xsl:template>

</xsl:stylesheet>