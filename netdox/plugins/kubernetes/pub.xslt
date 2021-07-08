<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:template match="/">
    <xsl:variable name="apps" select="json-to-xml(root)"/>
    <xsl:apply-templates select="$apps/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <document level="portable" type="references">
        <documentinfo>
            <uri title="Kubernetes Clusters" />
            <publication id="_nd_k8spub" title="Kubernetes Clusters" />
        </documentinfo>

        <section id="title">
            <fragment id="title">
                <heading level="1">Kubernetes Clusters</heading>
            </fragment>
        </section>

        <xsl:for-each select="xpf:map">
            <section id="cluster_{position()}" title="Cluster: {@key}">
                <xref-fragment id="cluster_{position()}_workers">
                    <xsl:for-each select="xpf:map">
                        <blockxref type="embed" frag="default" docid="{@key}" />
                    </xsl:for-each>
                </xref-fragment>
            </section>
        </xsl:for-each>
    </document>
</xsl:template>

</xsl:stylesheet>