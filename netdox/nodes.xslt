<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:include href="imports.xslt"/>

<xsl:template match="/">
    <xsl:variable name="nodes" select="json-to-xml(root)"/>
    <xsl:apply-templates select="$nodes/xpf:map/xpf:array[@key = 'objects']/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:result-document href="out/nodes/{xpf:string[@key = 'docid']}.psml">
        <document type="node" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="{xpf:string[@key = 'docid']}" title="{xpf:string[@key = 'name']}"/>
            </documentinfo>

            <metadata>
                <properties>
                    <property name="template_version"     title="Template version"   value="1.0" />
                </properties>
            </metadata>

            <section id="title">
                <fragment id="title">
                    <heading level="1">Node: <xsl:value-of select="xpf:string[@key = 'name']"/></heading>
                </fragment>
            </section>

            <section id="details" title="Node Details">

                <properties-fragment id="summary">
                    <property name="nodename" title="Name" value="{xpf:string[@key = 'name']}" />
                    <property name="nodetype" title="Node Type" value="{xpf:string[@key = 'type']}" />
                    <property name="location" title="Location" value="{xpf:string[@key='location']}" />
                </properties-fragment>

                <properties-fragment id="domains">
                    <xsl:for-each select="xpf:array[@key = 'domains']/xpf:string">
                        <property name="domain" title="Domain" datatype="xref">
                            <xref frag="default" docid="_nd_domain_{translate(.,'.','_')}" />
                        </property>
                    </xsl:for-each>
                </properties-fragment>

                <properties-fragment id="ips">
                    <xsl:if test="xpf:string[@key = 'private_ip']">
                        <property name="ipv4" title="Private IP" datatype="xref">
                            <xref frag="default" docid="_nd_ip_{translate(xpf:string[@key = 'private_ip'],'.','_')}" />
                        </property>
                    </xsl:if>
                    <xsl:for-each select="xpf:array[@key = 'public_ips']/xpf:string">
                        <property name="ipv4" title="Public IP" datatype="xref">
                            <xref frag="default" docid="_nd_ip_{translate(.,'.','_')}" />
                        </property>
                    </xsl:for-each>
                </properties-fragment>

            </section>

            <xsl:apply-templates select="." mode="nodebody" />

            <section id="other" >
                <xsl:apply-templates select="." mode="nodefooter" />
            </section>

        </document>
    </xsl:result-document>
</xsl:template>

<xsl:template match="text()" mode="nodebody" />
<xsl:template match="text()" mode="nodefooter" />

</xsl:stylesheet>