<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="date" select="format-date(current-date(), '[Y0001]-[M01]-[D01]')"/>
<document level="portable">
    <documentinfo>
        <uri title="Status Update" docid="_nd_status_update"><labels>show-reversexrefs</labels></uri>
    </documentinfo>

    <section id="title">
        <fragment id="title">
            <heading level="1">Status update for <xsl:value-of select="$date"/></heading>
        </fragment>
    </section>

    <xsl:apply-templates select="." mode="status" />

</document>
</xsl:template>

<xsl:template match="text()" mode="status" />

</xsl:stylesheet>