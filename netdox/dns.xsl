<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="dns" select="json-to-xml(dns)"/>
    <xsl:apply-templates select="$dns/xpf:map/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:variable name="name" select="@key"/>
    <xsl:try>
        <xsl:result-document href="out/DNS/{translate($name,'.','_')}.psml" method="xml" indent="yes">
            <document type="dns" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <xsl:variable name="labels">
                <xsl:for-each select="xpf:array[@key = 'labels']/xpf:string">,<xsl:value-of select="."/></xsl:for-each>
            </xsl:variable>

                <documentinfo>
                    <uri docid="_nd_{translate($name,'.','_')}" title="{$name}">
                        <labels>show-reversexrefs<xsl:value-of select="$labels"/></labels>
                    </uri>
                </documentinfo>

                <metadata>
                    <properties>
                        <property name="template_version"     title="Template version"   value="5.1" />
                    </properties>
                </metadata>

                <section id="title">
                    <fragment id="title">
                        <heading level="2">DNS Record</heading>
                    <xsl:choose>
                        <xsl:when test="contains($name, '_wildcard_')">
                            <heading level="1"><xsl:value-of select="replace($name,'_wildcard_','*')"/></heading>
                        </xsl:when>
                        <xsl:otherwise>
                            <heading level="1"><link href="https://{$name}"><xsl:value-of select="$name"/></link></heading>
                        </xsl:otherwise>
                    </xsl:choose>
                    </fragment>
                </section>

                <section id="details" title="details">

                    <properties-fragment id="info">
                        <property name="name"       title="Name"        value="{$name}" />
                        <property name="root"       title="Root Domain"        value="{xpf:string[@key = 'root']}" />
                        <property name="source"     title="DNS Source"      value="{xpf:string[@key = 'source']}" />
                        <property name="role"       title="DNS Role"    datatype="xref">
                            <xref frag="default" docid="_nd_role_{xpf:string[@key = 'role']}" />
                        </property>
                        <xsl:choose>
                            <xsl:when test="xpf:string[@key = 'license']">
                        <property name="license"     title="PageSeeder License"      datatype="xref" >
                            <xref frag="default" uriid="{xpf:string[@key = 'license']}" reversetitle="Domain using this license"/>
                        </property>
                            </xsl:when>
                            <xsl:otherwise>
                        <property name="license" title="PageSeeder License" value="—" />
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:choose>
                            <xsl:when test="xpf:string[@key = 'org']">
                        <property name="organization"     title="Licensed Organization"      datatype="xref" >
                            <xref frag="default" uriid="{xpf:string[@key = 'org']}" reversetitle="Domain using license issued to this organization."/>
                        </property>
                            </xsl:when>
                            <xsl:otherwise>
                        <property name="organization" title="Licensed Organization" value="—" />
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:choose>
                            <xsl:when test="not(xpf:string[@key='location']/text() = null)">
                        <property name="location" title="Location" value="{xpf:string[@key = 'location']}" />
                            </xsl:when>
                            <xsl:otherwise>
                        <property name="location" title="Location" value="—" />
                            </xsl:otherwise>
                        </xsl:choose>
                    </properties-fragment>

                    <properties-fragment id="dest">
                    <xsl:for-each select="xpf:array[@key = 'private_ips']/xpf:string">
                        <property name="ipv4" title="Private IP" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this IP"><xsl:value-of select="."/></xref>
                        </property>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:array[@key = 'public_ips']/xpf:string">
                        <property name="ipv4" title="Public IP" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this IP"><xsl:value-of select="."/></xref>
                        </property>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:array[@key = 'domains']/xpf:string">
                        <xsl:choose>
                            <xsl:when test="not(string-length(.) > 75)">
                        <property name="cname" title="CNAME" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this domain"><xsl:value-of select="."/></xref>
                        </property>
                            </xsl:when>
                            <xsl:otherwise>
                        <property name="cname" title="CNAME" value="{.}" />
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:array[@key = 'apps']/xpf:string">
                        <property name="app" title="Application" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this app"><xsl:value-of select="."/></xref>
                        </property>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:array[@key = 'vms']/xpf:string">
                        <property name="vm" title="VM" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this VM"><xsl:value-of select="."/></xref>
                        </property>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:array[@key = 'ec2s']/xpf:string">
                        <property name="ec2" title="AWS EC2 Instance" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(.,'.','_')}" reversetitle="DNS record resolving to this instance"><xsl:value-of select="."/></xref>
                        </property>
                    </xsl:for-each>
                    </properties-fragment>
                    
                    <properties-fragment id="subnets">
                    <xsl:for-each select="xpf:array[@key = 'subnets']/xpf:string">
                        <property name="subnet" title="Subnet" value="{.}" />
                    </xsl:for-each>
                    </properties-fragment>

                    <properties-fragment id="icinga">
                    <xsl:for-each select="xpf:map[@key = 'icinga']/xpf:map">
                        <property name="icinga" title="Icinga Hostname" datatype="xref">
                            <xref frag="default" docid="{translate(@key,'.','_')}" />
                        </property>
                        <xsl:for-each select="xpf:array">
                        <property name="host" title="Host Display Name" value="{@key}" />
                            <xsl:for-each select="xpf:string">
                        <property name="service" title="Service Display Name" value="{substring-after(., '!')}" />
                            </xsl:for-each>
                        </xsl:for-each>
                    </xsl:for-each>
                    </properties-fragment>

                    <fragment id="screenshot" labels="text-align-center">
                        <block label="border-2">
                            <image src="/ps/operations/network/website/screenshots/{translate($name,'.','_')}.jpg"/>
                        </block>
                    </fragment>
                    
                    <properties-fragment id="url-key">
                        <property name="url-key" title="URL Key" value="" />
                    </properties-fragment>
    
                    <properties-fragment id="for-search" labels="s-hide-content">
                        <xsl:variable name="octets">
                            <xsl:for-each select="xpf:array[matches(@key, '.*_ips$')]/xpf:string">
                                <xsl:value-of select="concat(tokenize(.,'\.')[3], ', ', concat(tokenize(.,'\.')[3],'.',tokenize(.,'\.')[4]), ', ')"/>
                            </xsl:for-each>
                        </xsl:variable>
                        <property name="octets" title="Octets for search" value="{substring($octets,1,string-length($octets)-2)}"/>
                    </properties-fragment>
                    
                </section>
            
            </document>
        </xsl:result-document>
        <xsl:catch>
            <xsl:message>[ERROR][dns.xsl] The transformation threw an exception.
            [ERROR][dns.xsl] Error code: <xsl:value-of select="$err:code"/>
            [ERROR][dns.xsl] Error description: <xsl:value-of select="$err:description"/>
            [ERROR][dns.xsl] ****END****</xsl:message>
        </xsl:catch>
    </xsl:try>
</xsl:template>

</xsl:stylesheet>