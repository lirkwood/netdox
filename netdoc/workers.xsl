<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="workers" select="json-to-xml(workers)"/>
    <xsl:apply-templates select="$workers/xpf:map/xpf:map/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:variable name="name" select="@key"/>
    <xsl:result-document href="outgoing/k8s/_nd_{translate($name,'.','_')}.psml" method="xml" indent="yes">
        <document type="k8s_worker" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="_nd_{translate($name,'.','_')}" title="worker: {$name}"><labels>show-reversexrefs</labels></uri>
            </documentinfo>

            <metadata>
                <properties>
                    <property name="template_version"     title="Template version"   value="1.0" />
                </properties>
            </metadata>

            <section id="title">
                <fragment id="title">
                    <heading level="1">worker: <xsl:value-of select="$name"/></heading>
                </fragment>

                <properties-fragment id="vm">
                    <property name="vm" title="Host VM" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'vm'],'.','_')}" />
                    </property>
                </properties-fragment>
            </section>

            <section id="apps" title="Apps">

                <xref-fragment id="apps">
                <xsl:for-each select="xpf:array[@key = 'apps']/xpf:string">
                    <blockxref frag="default" type="embed" docid="_nd_{translate(.,'.','_')}" />
                </xsl:for-each>
                </xref-fragment>
            </section>

        </document>
    </xsl:result-document>
</xsl:template>

</xsl:stylesheet>