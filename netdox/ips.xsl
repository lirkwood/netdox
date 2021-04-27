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
    <xsl:variable name="subnetdir" select="translate(xpf:string[@key = 'subnet'],'/','_')"/>
    <xsl:result-document href="out/IPs/{$subnetdir}/{translate(@key,'.','_')}.psml" method="xml" indent="yes">
    <document type="ip" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <documentinfo>
            <uri docid="_nd_{translate(@key,'.','_')}" title="{@key}"><labels>show-reversexrefs</labels></uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="2.0" />
            </properties>
        </metadata>

        <section id="title">
            <fragment id="title">
                <heading level="2">IP Address</heading>
                <heading level="1"><xsl:value-of select="@key"/></heading>
            </fragment>
        </section>

        <section id="details" title="details">
        
            <properties-fragment id="addresses">
                <property name="ipv4"               title="IP"          value="{@key}" /> 
                <property name="subnet"               title="Subnet"          value="{xpf:string[@key = 'subnet']}" />
                <property name="location"               title="Location"          value="{xpf:string[@key = 'location']}" />
                <property name="nat" title="NAT Destination" datatype="xref">
                    <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'nat'],'.','_')}"
                    reversetitle="NAT alias" />
                </property>
                <property name="source" title="DNS Source" value="{xpf:string[@key = 'source']}" />
            </properties-fragment>

            <properties-fragment id="reversedns">
            <xsl:for-each select="xpf:array[@key = 'ptr']/xpf:string">
                <property name="ptr" title="Reverse DNS Record" datatype="xref">
                    <xref frag="default" docid="_nd_{translate(.,'.','_')}"
                    reversetitle="Reverse DNS destination" />
                </property>
            </xsl:for-each>
            </properties-fragment>

            <properties-fragment id="for-search" labels="s-hide-content">
                <property name="octets" title="Octets for search" value="{xpf:string[@key = 'for-search']}"/>
            </properties-fragment>
            
        </section> 

    </document>
    </xsl:result-document>
</xsl:template>

</xsl:stylesheet>