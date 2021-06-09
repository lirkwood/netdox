<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:template match="/">
    <xsl:variable name="apps" select="json-to-xml(apps)"/>
    <xsl:apply-templates select="$apps/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <document level="portable" type="references">
        <documentinfo>
            <uri title="Kubernetes Clusters" />
            <publication id="_nd_k8s_pub" title="Kubernetes Clusters" />
        </documentinfo>

        <section id="title">
            <fragment id="title">
                <heading level="1">Kubernetes Clusters</heading>
            </fragment>
        </section>

        <section id="xrefs">
            <xref-fragment id="clusters">
            <xsl:for-each select="xpf:map">
                <blockxref docid="_nd_{translate(@key,'.','_')}" frag="default" type="embed" />
            </xsl:for-each>
            </xref-fragment>
        </section>
    </document>
</xsl:template>

</xsl:stylesheet>