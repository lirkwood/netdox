<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:template match="/">
    <xsl:variable name="pools" select="json-to-xml(root)"/>
    <xsl:apply-templates select="$pools/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <document level="portable" type="references">
        <documentinfo>
            <uri title="Xen Orchestra Pools" />
            <publication id="_nd_xopub" title="Xen Orchestra Pools" />
        </documentinfo>

        <section id="title">
            <fragment id="title">
                <heading level="1">Xen Orchestra Pools</heading>
            </fragment>
        </section>

        <section id="pools">
        <xsl:for-each select="xpf:array">
            <fragment id="title_{position()}">
                <heading level="2"><xsl:value-of select="@key" /></heading>
            </fragment>
            <xref-fragment id="pool_{position()}_hosts">
            <xsl:for-each select="xpf:string">
                <blockxref docid="_nd_node_xohost_{.}" frag="default" type="embed"></blockxref>
            </xsl:for-each>
            </xref-fragment>
        </xsl:for-each>
        </section>
    </document>
</xsl:template>

</xsl:stylesheet>