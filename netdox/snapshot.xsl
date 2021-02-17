<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="dns" select="json-to-xml(dns)"/>
    <xsl:apply-templates select="$dns/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
        <document type="snapshot" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="_nd_snapshot_{format-date(current-date(), '[Y0001]-[M01]-[D01]')}" title="DNS Snapshot on {format-date(current-date(), '[Y0001]-[M01]-[D01]')}"><labels>show-reversexrefs</labels></uri>
            </documentinfo>

            <metadata>
                <properties>
                    <property name="template_version"     title="Template version"   value="1.0" />
                </properties>
            </metadata>

            <section id="title">
                <fragment id="title">
                    <heading level="1">DNS Snapshot on <xsl:value-of select="format-date(current-date(), '[Y0001]-[M01]-[D01]')"/></heading>
                </fragment>
            </section>

            <section id="details">
                <xsl:for-each select="./xpf:map">
                <fragment id="heading_{position()}">
                    <heading level='2'>
                        <link href="https://{@key}"><xsl:value-of select="@key"/></link>
                    </heading>
                </fragment>
                <properties-fragment id="info_{position()}">
                    <property name="domain"       title="Domain"        value="{@key}" />
                    <property name="root"       title="Root"        value="{xpf:string[@key = 'root']}" />
                    <property name="source"     title="Source"      value="{xpf:string[@key = 'source']}" />
                    <property name="client"     title="Client"      value="" />
                </properties-fragment>

                <properties-fragment id="dest_{position()}">
                <xsl:for-each select="xpf:map/xpf:map[@key = 'ips']/xpf:array[@key = 'private']/xpf:string">
                    <property name="ipv4" title="Private IP" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" />
                    </property>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:map[@key = 'ips']/xpf:array[@key = 'public']/xpf:string">
                    <property name="ipv4" title="Public IP" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" />
                    </property>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:array[@key = 'domains']/xpf:string">
                    <xsl:choose>
                        <xsl:when test="not(string-length(.) > 75)">
                    <property name="alias" title="Alias to" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" />
                    </property>
                        </xsl:when>
                        <xsl:otherwise>
                    <property name="alias" title="Alias to" value="{.}" />
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:array[@key = 'apps']/xpf:string">
                    <property name="app" title="Application" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" />
                    </property>
                </xsl:for-each>
                </properties-fragment>
                
                <properties-fragment id="subnets_{position()}">
                <xsl:for-each select="xpf:array[@key = 'subnets']/xpf:string">
                    <property name="subnet" title="Subnet" value="{.}" />
                </xsl:for-each>
                </properties-fragment>
                </xsl:for-each>
            </section>

        </document>
</xsl:template>
</xsl:stylesheet>