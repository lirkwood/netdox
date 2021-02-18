<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="ips" select="json-to-xml(ips)"/>
    <xsl:apply-templates select="$ips/xpf:map/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <document type="ip" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="1.5" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="1"><xsl:value-of select="@key"/></heading>
            </fragment>
        </section>

        <section id="details" title="details">
        
            <properties-fragment id="addresses">
                <property name="network"               title="Network"          value="" />
                <property name="subnet"               title="subnet"          value="{xpf:string[@key = 'subnet']}" />
                <property name="ipv4"               title="IP"          value="{@key}" /> 
                <property name="source" title="Source" value="{xpf:string[@key = 'source']}" />
                <property name="ipv4_3"              title="Octet 3"      value = "{xpf:string[@key = 'o3']}" />
                <property name="ipv4_3-4"              title="Octets 3-4"      value = "{xpf:string[@key = 'o3-4']}" />
            </properties-fragment>
    
            <properties-fragment id="nat">
            <xsl:for-each select="xpf:map[@key = 'nat']/xpf:string">
                <property name="nat_dest" title="NAT Destination" datatype="xref">
                    <xref frag="default" docid="_nd_{translate(.,'.','_')}"
                    reversetitle="NAT alias" />
                </property>
            </xsl:for-each>
            </properties-fragment>
        
            <properties-fragment id="ports">
            <xsl:for-each select="xpf:map[@key = 'ports']/xpf:string">
                <property name="port"               title="{.} port"          value="Port {@key}" />
            </xsl:for-each>
            </properties-fragment>

            <properties-fragment id="reversedns">
            <xsl:for-each select="xpf:map[@key = 'ptr']">
                <property name="ptr" title="Reverse DNS Record" datatype="xref">
                    <xref frag="default" docid="_nd_{translate(.,'.','_')}"
                    reversetitle="Reverse DNS destination" />
                </property>
            </xsl:for-each>
            </properties-fragment>
            
        </section> 

    </document>
</xsl:template>

</xsl:stylesheet>