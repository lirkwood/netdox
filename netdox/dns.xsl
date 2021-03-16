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
    <xsl:result-document href="out/DNS/{translate($name,'.','_')}.psml" method="xml" indent="yes">
        <document type="dns" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="_nd_{translate($name,'.','_')}" title="dns: {$name}"><labels>show-reversexrefs</labels></uri>
            </documentinfo>

            <metadata>
                <properties>
                    <property name="template_version"     title="Template version"   value="4.1" />
                </properties>
            </metadata>

            <section id="title">
                <fragment id="title">
                <xsl:choose>
                    <xsl:when test="contains($name, '_wildcard_')">
                        <heading level="1">dns: <xsl:value-of select="replace($name,'_wildcard_','*.')"/></heading>
                    </xsl:when>
                    <xsl:otherwise>
                        <heading level="1">dns: <xsl:value-of select="$name"/></heading>
                    </xsl:otherwise>
                </xsl:choose>
                </fragment>
            </section>

            <section id="details" title="details">

                <properties-fragment id="info">
                    <property name="domain"       title="Domain"        value="{$name}" />
                    <property name="root"       title="Root"        value="{xpf:string[@key = 'root']}" />
                    <property name="source"     title="Source"      value="{xpf:string[@key = 'source']}" />
                    <property name="icinga"     title="Icinga Display Name"      value="{xpf:string[@key = 'icinga']}" />
                    <property name="client"     title="Client"      value="" />
                </properties-fragment>

                <properties-fragment id="dest">
                <xsl:for-each select="xpf:map/xpf:map[@key = 'ips']/xpf:array[@key = 'private']/xpf:string">
                    <property name="ipv4" title="Private IP" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this IP"/>
                    </property>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:map[@key = 'ips']/xpf:array[@key = 'public']/xpf:string">
                    <property name="ipv4" title="Public IP" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this IP"/>
                    </property>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:array[@key = 'domains']/xpf:string">
                    <xsl:choose>
                        <xsl:when test="not(string-length(.) > 75)">
                    <property name="alias" title="Alias to" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this domain"/>
                    </property>
                        </xsl:when>
                        <xsl:otherwise>
                    <property name="alias" title="Alias to" value="{.}" />
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:array[@key = 'nat']/xpf:string">
                    <property name="nat_dest" title="NAT Destination" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="NAT alias"/>
                    </property>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:array[@key = 'apps']/xpf:string">
                    <property name="app" title="Application" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this app"/>
                    </property>
                </xsl:for-each>
                <xsl:for-each select="xpf:map/xpf:array[@key = 'vms']/xpf:string">
                    <property name="vm" title="VM" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this VM"/>
                    </property>
                </xsl:for-each>
                </properties-fragment>
                
                <properties-fragment id="subnets">
                <xsl:for-each select="xpf:array[@key = 'subnets']/xpf:string">
                    <property name="subnet" title="Subnet" value="{.}" />
                </xsl:for-each>
                </properties-fragment>

                <fragment id="screenshot" labels="text-align-center">
                    <block label="border-2">
                        <image src="/ps/operations/network/website/screenshots/{translate($name,'.','_')}.jpg"/>
                    </block>
                </fragment>

                <properties-fragment id="secrets">
                    <xsl:for-each select="xpf:map[@key = 'secrets']/xpf:string">
                        <property name="secret" title="Secret" datatype="link">
                            <link href="https://secret.allette.com.au/app/#/secret/{@key}/general">"<xsl:value-of select="substring-before(.,';')"/>" (<xsl:value-of select="substring-after(.,';')"/>)</link>
                        </property>
                    </xsl:for-each>
                </properties-fragment>

                <properties-fragment id="for-search" labels="s-hide-content">
                    <xsl:variable name="octets">
                        <xsl:for-each select="xpf:map/xpf:map[@key = 'ips']/xpf:array/xpf:string">
                            <xsl:value-of select="concat(tokenize(.,'\.')[3], ', ', concat(tokenize(.,'\.')[3],'.',tokenize(.,'\.')[4]), ', ')"/>
                        </xsl:for-each>
                    </xsl:variable>
                    <property name="octets" title="Octets for search" value="{substring($octets,1,string-length($octets)-2)}"/>
                </properties-fragment>
                
            </section>
            
            <section id="ansible" title="Ansible"/>
        
        </document>
    </xsl:result-document>
</xsl:template>

</xsl:stylesheet>