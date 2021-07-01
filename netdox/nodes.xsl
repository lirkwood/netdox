<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:template match="/">
    <xsl:variable name="nodes" select="json-to-xml(nodes)"/>
    <xsl:apply-templates select="$nodes/xpf:map/xpf:array[@key = 'objects']/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:variable name="name" select="xpf:string[@key = 'name']"/>
    <xsl:result-document href="out/nodes/{translate($name,'.','_')}.psml">
        <document type="node" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="{xpf:string[@key = 'docid']}" title="{$name}"/>
            </documentinfo>

            <metadata>
                <properties>
                    <property name="template_version"     title="Template version"   value="1.0" />
                </properties>
            </metadata>

            <section id="network" title="Network Details">

                <properties-fragment id="domains">
                    <xsl:for-each select="xpf:array[@key = 'domains']/xpf:string">
                        <property name="domain" title="Domain" datatype="xref">
                            <xref frag="default" docid="_nd_domain_{.}" />
                        </property>
                    </xsl:for-each>
                </properties-fragment>

                <properties-fragment id="ips">
                    <property name="ipv4" title="Private IP" datatype="xref">
                        <xref frag="default" docid="_nd_ip_{translate(xpf:string[@key = '_private_ip'],'.','_')}" />
                    </property>
                    <xsl:for-each select="xpf:array[@key = '_public_ips']/xpf:string">
                        <property name="ipv4" title="Public IP" datatype="xref">
                            <xref frag="default" docid="_nd_ip_{translate(.,'.','_')}" />
                        </property>
                    </xsl:for-each>
                </properties-fragment>

            </section>
            <section id="details"/>
            <section id="plugininf"/>

        </document>
    </xsl:result-document>
</xsl:template>

</xsl:stylesheet>