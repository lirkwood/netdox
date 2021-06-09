<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:template match="/">
    <xsl:variable name="pools" select="json-to-xml(pools)"/>
    <xsl:apply-templates select="$pools/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <document level="portable" type="references">
        <documentinfo>
            <uri title="Xen Orchestra Pools" />
            <publication id="_nd_xo_pub" title="Xen Orchestra Pools" />
        </documentinfo>

        <section id="title">
            <fragment id="title">
                <heading level="1">Xen Orchestra Pools</heading>
            </fragment>
        </section>

        <section id="xrefs">
            <xref-fragment id="pools">
            <xsl:for-each select="xpf:map">
                <blockxref docid="_nd_{@key}" frag="default" type="embed"><xsl:value-of select="xpf:string[@key='name_label']"/></blockxref>
            </xsl:for-each>
            </xref-fragment>
        </section>
    </document>
</xsl:template>

</xsl:stylesheet>