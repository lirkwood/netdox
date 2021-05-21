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

        <xsl:variable name="labels">
            <xsl:for-each select="xpf:array[@key = 'labels']/xpf:string">,<xsl:value-of select="."/></xsl:for-each>
            <xsl:if test="xpf:boolean[@key = 'unused'] = true()">,unused</xsl:if>
        </xsl:variable>

        <documentinfo>
            <uri docid="_nd_{translate(@key,'.','_')}" title="{@key}">
                <labels>show-reversexrefs<xsl:value-of select="$labels"/></labels>
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="2.1" />
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
                <xsl:if test="xpf:string[@key = 'nat']">
                <property name="nat" title="NAT Destination" datatype="xref">
                    <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'nat'],'.','_')}" reversetitle="NAT alias" />
                </property>
                </xsl:if>
            </properties-fragment>

        </section>
        <section id="reversedns" title="Reverse DNS Records">
            <xsl:for-each select="xpf:array[@key = 'ptr']/xpf:array">
            <properties-fragment id="ptr_{position()}">
                <property name="ptr" title="PTR Record" datatype="xref">
                    <xref frag="default" docid="_nd_{translate(xpf:string[1],'.','_')}" reversetitle="Reverse DNS destination" />
                </property>
                <property name="source" title="Source Plugin" value="{xpf:string[2]}"/>
            </properties-fragment>
            </xsl:for-each>

            <properties-fragment id="impliedptr">
            <xsl:for-each select="xpf:array[@key = 'implied_ptr']/xpf:string">
                <property name="impliedptr" title="Implied PTR Record" datatype="xref" >
                    <xref frag="default" docid="_nd_{translate(.,'.','_')}" />
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