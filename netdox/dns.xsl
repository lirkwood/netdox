<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />
<xsl:variable name="config" select="json-to-xml(unparsed-text('src/config.json'))/xpf:map"/>
<xsl:variable name="auth" select="json-to-xml(unparsed-text('src/authentication.json'))/xpf:map"/>

<xsl:template match="/">
    <xsl:variable name="dns" select="json-to-xml(forward)"/>
    <xsl:apply-templates select="$dns/xpf:map/xpf:array[@key = 'records']/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:variable name="name" select="xpf:string[@key = 'name']"/>
    <xsl:try>
        <xsl:result-document href="out/DNS/{translate($name,'.','_')}.psml" method="xml" indent="yes">
            <document type="dns" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <xsl:variable name="labels">
                <xsl:for-each select="xpf:array[@key = 'labels']/xpf:string">,<xsl:value-of select="."/></xsl:for-each>
            </xsl:variable>
            <xsl:variable name="role" select="xpf:string[@key = 'role']/text()"/>

                <documentinfo>
                    <uri docid="_nd_{translate($name,'.','_')}" title="{$name}">
                        <labels>show-reversexrefs<xsl:value-of select="$labels"/></labels>
                    </uri>
                </documentinfo>

                <metadata>
                    <properties>
                        <property name="template_version"     title="Template version"   value="6.0" />
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
                        <property name="role"       title="DNS Role"    datatype="xref">
                        <xsl:if test="xpf:string[@key = 'role']">
                            <xref frag="default" docid="_nd_role_{$role}" />
                        </xsl:if>
                        </property>
                        <xsl:choose>
                            <xsl:when test="string-length(xpf:string[@key = 'location']) != 0">
                        <property name="location" title="Location" value="{xpf:string[@key = 'location']}" />
                            </xsl:when>
                            <xsl:otherwise>
                        <property name="location" title="Location" value="—" />
                            </xsl:otherwise>
                        </xsl:choose>
                        <xsl:if test="$role = 'pageseeder'">
                            <xsl:if test="string-length(xpf:string[@key = 'license']) != 0">
                        <property name="license"     title="PageSeeder License"      datatype="xref" >
                            <xref frag="default" uriid="{xpf:string[@key = 'license']}" reversetitle="Domain using this license"/>
                        </property>
                        <property name="organization"     title="Licensed Organization"      datatype="xref" >
                            <xsl:if test="string-length(xpf:string[@key='org']) != 0">
                            <xref frag="default" uriid="{xpf:string[@key = 'org']}" reversetitle="Domain using license issued to this organization."/>
                            </xsl:if>
                        </property>
                            </xsl:if>
                        </xsl:if>
                    </properties-fragment>
                </section>
                <section id="dest" title="Destinations">

                    <xsl:for-each select="xpf:array[@key = '_private_ips']/xpf:array">
                    <properties-fragment id="private_ip_{position()}">
                        <property name="ipv4" title="Private IP" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(xpf:string[1],'.','_')}" reversetitle="DNS record resolving to this IP"><xsl:value-of select="xpf:string[1]"/></xref>
                        </property>
                        <property name="source" title="Source Plugin" value="{xpf:string[2]}" />
                    </properties-fragment>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:array[@key = '_public_ips']/xpf:array">
                    <properties-fragment id="public_ip_{position()}">
                        <property name="ipv4" title="Public IP" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(xpf:string[1],'.','_')}" reversetitle="DNS record resolving to this IP"><xsl:value-of select="xpf:string[1]"/></xref>
                        </property>
                        <property name="source" title="Source Plugin" value="{xpf:string[2]}" />
                    </properties-fragment>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:array[@key = '_cnames']/xpf:array">
                    <properties-fragment id="cname_{position()}">
                        <property name="cname" title="CNAME" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(xpf:string[1],'.','_')}" reversetitle="DNS record resolving to this domain"><xsl:value-of select="xpf:string[1]"/></xref>
                        </property>
                        <property name="source" title="Source Plugin" value="{xpf:string[2]}" />
                    </properties-fragment>
                    </xsl:for-each>

                    <xsl:for-each select="xpf:map[@key='resources']/xpf:array">
                        <xsl:variable name="plugin" select="@key"/>
                        <xsl:for-each select="xpf:string">
                    <properties-fragment id="{$plugin}_{position()}">
                        <property name="resource" title="Resource" datatype="xref">
                            <xref frag="default" docid="_nd_{.}" />
                        </property>
                        <property name="source" title="Source Plugin" value="{$plugin}"/>
                    </properties-fragment>
                        </xsl:for-each>
                    </xsl:for-each>
                    
                    <properties-fragment id="subnets">
                    <xsl:for-each select="xpf:array[@key = 'subnets']/xpf:string">
                        <property name="subnet" title="Subnet" value="{.}" />
                    </xsl:for-each>
                    </properties-fragment>

                    <xsl:if test="$config/xpf:map[@key = $role]/*[@key = 'screenshot'] = '1'">
                    <fragment id="screenshot" labels="text-align-center">
                        <block label="border-2">
                            <image src="/ps/{translate($auth/xpf:map[@key='pageseeder']/xpf:string[@key='group'],'-','/')}/website/screenshots/{translate($name,'.','_')}.jpg"/>
                        </block>
                    </fragment>
                    </xsl:if>
    
                    <properties-fragment id="for-search" labels="s-hide-content">
                        <xsl:variable name="octets">
                            <xsl:for-each select="xpf:array[matches(@key, '.*_ips$')]/xpf:array">
                                <xsl:value-of select="concat(tokenize(xpf:string[1],'\.')[3], ', ', concat(tokenize(xpf:string[1],'\.')[3],'.',tokenize(xpf:string[1],'\.')[4]), ', ')"/>
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