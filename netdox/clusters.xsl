<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="workers" select="json-to-xml(workers)"/>
    <xsl:apply-templates select="$workers/xpf:map/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:variable name="name" select="@key"/>
    <xsl:result-document href="out/k8s/{$name}/{translate($name,'.','_')}.psml" method="xml" indent="yes">
        <document type="k8s_cluster" level="portable" xmlns:t="http://pageseeder.com/psml/template">

            <documentinfo>
                <uri docid="_nd_{translate($name,'.','_')}" title="k8s_cluster: {$name}"><labels>show-reversexrefs</labels></uri>
            </documentinfo>

            <section id="title">
                <fragment id="1">
                <heading level="1">k8s_cluster: <xsl:value-of select="$name"/></heading>
                </fragment>
            </section>

            <section id="nodes">
                <xref-fragment id="workers">
                <xsl:for-each select="xpf:map">
                    <blockxref frag="default" type="embed" docid="_nd_{translate(@key,'.','_')}"
                    reversetitle="Cluster this worker belongs to"/>
                </xsl:for-each>
                </xref-fragment>
            </section>
        
        </document>

    </xsl:result-document>
</xsl:template>

</xsl:stylesheet>