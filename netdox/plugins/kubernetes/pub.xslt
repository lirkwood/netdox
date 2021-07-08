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

        <section id="clusters">
            <xsl:for-each select="xpf:map">
                <fragment id="title_{position()}">
                    <heading level="2"><xsl:value-of select="@key" /></heading>
                </fragment>
                <xref-fragment id="cluster_{position()}_workers">
                    <xsl:for-each select="xpf:array">
                        <blockxref type="embed" frag="default" docid="{@key}" />
                    </xsl:for-each>
                </xref-fragment>
            </xsl:for-each>
        </section>
    </document>
</xsl:template>

</xsl:stylesheet>