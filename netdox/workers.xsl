<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="workers" select="json-to-xml(workers)"/>
    <xsl:for-each select="$workers/xpf:map/xpf:map">
        <xsl:apply-templates select="xpf:map">
            <xsl:with-param name="context" select="@key"/>
        </xsl:apply-templates>
    </xsl:for-each>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:param name="context"/>
    <xsl:variable name="name" select="@key"/>
    <xsl:result-document href="out/k8s/{$context}/{translate($name,'.','_')}.psml" method="xml" indent="yes">
        <document type="k8s_worker" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="_nd_{translate($name,'.','_')}" title="k8s_worker: {$name}"><labels>show-reversexrefs</labels></uri>
            </documentinfo>

            <metadata>
                <properties>
                    <property name="template_version"     title="Template version"   value="1.0" />
                </properties>
            </metadata>

            <section id="title">
                <fragment id="title">
                    <heading level="2">Kubernetes Worker</heading>
                    <heading level="1"><xsl:value-of select="$name"/></heading>
                </fragment>

                <properties-fragment id="vm">
                    <xsl:for-each select="xpf:string[@key = 'vm']">
                    <property name="vm" title="Host VM" datatype="xref">
                        <xref frag="default" docid="_nd_{translate(.,'.','_')}" 
                        reversetitle="Kubernetes worker in this VM"/>
                    </property>
                    </xsl:for-each>
                </properties-fragment>
            </section>

            <section id="apps" title="Apps">

                <xref-fragment id="apps">
                <xsl:for-each select="xpf:array[@key = 'apps']/xpf:string">
                    <blockxref frag="default" type="embed" docid="_nd_{translate(.,'.','_')}" 
                    reversetitle="Kubernetes worker running this app"/>
                </xsl:for-each>
                </xref-fragment>
                
            </section>

        </document>
    </xsl:result-document>
</xsl:template>

</xsl:stylesheet>