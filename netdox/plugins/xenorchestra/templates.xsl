<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="templates" select="json-to-xml(templates)"/>
    <xsl:apply-templates select="$templates/xpf:map"/>
</xsl:template>

<xsl:template match="xpf:map">
    <document level="portable">
    <documentinfo>
      <uri title="VM Templates" docid="_nd_templates"><labels>show-reversexrefs</labels></uri>
    </documentinfo>
    <section id="title">
        <fragment id="title">
            <heading level="1">Templates for VM creation</heading>
        </fragment>
    </section>
    <section id="templates">
        <fragment id="vms">
            <heading level="2">VMs Running Now</heading>
            <xsl:for-each select="xpf:map[@key = 'vms']/xpf:string">
                <para><xsl:value-of select="@key"/>:    <xref frag="default" docid="_nd_{.}"/></para>
            </xsl:for-each>
        </fragment>
        <fragment id="snapshots">
            <heading level="2">VM Snapshots</heading>
            <xsl:for-each select="xpf:map[@key = 'snapshots']/xpf:string">
                <para><xsl:value-of select="@key"/>:    <xsl:value-of select="."/></para>
            </xsl:for-each>
        </fragment>
        <fragment id="templates">
            <heading level="2">VM Templates</heading>
            <xsl:for-each select="xpf:map[@key = 'templates']/xpf:string">
                <para><xsl:value-of select="@key"/>:    <xsl:value-of select="."/></para>
            </xsl:for-each>
        </fragment>
    </section>
    </document>
</xsl:template>

</xsl:stylesheet>