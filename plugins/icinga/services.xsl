<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />
<xsl:variable name="domains" select="json-to-xml(unparsed-text('/opt/app/src/domains.json'))"/>
<xsl:variable name="slugname" select="substring-before(tokenize(base-uri(), '/')[last()], '.psml')"/>

<xsl:template match="/">
    <xsl:result-document href="{$slugname}.psml">
        <xsl:apply-templates/>
    </xsl:result-document>
</xsl:template>

<xsl:template match="*">
    <xsl:copy>
        <xsl:copy-of select="@*"/>
        <xsl:apply-templates/>
    </xsl:copy>
</xsl:template>


<xsl:template match="section[@id = 'plugininf']">
    <xsl:copy>
        <xsl:copy-of select="@*"/>
        <xsl:apply-templates select="$domains//xpf:string[@key = 'name' and text() = translate($slugname,'_','.')]"/>
    </xsl:copy>
</xsl:template>

<xsl:template match="xpf:string[@key = 'name']">
    <xsl:variable name="context" select="parent::xpf:map/xpf:map[@key = 'icinga']"/>
    <properties-fragment id="icinga">
    <xsl:if test="$context/*">
        <property name="host" title="Host Display Name" value="{$context/xpf:string[@key = 'display']}" />
        <property name="template" title="Monitor Template" value="{$context/xpf:array[@key = 'templates']/xpf:string[1]}" />
        <xsl:for-each select="$context/xpf:array[@key = 'services']/xpf:string">
        <property name="service" title="Service Display Name" value="{.}" />
        </xsl:for-each>
    </xsl:if>
    </properties-fragment>
</xsl:template>

</xsl:stylesheet>