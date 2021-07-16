<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="xpf:map[xpf:map[@key = 'icinga']]" mode="domainfooter">
    <properties-fragment id="icinga">
        <property name="icinga" title="Icinga Instance" value="{xpf:string[@key = 'icinga']}" />
        <property name="host" title="Host Display Name" value="{xpf:string[@key = 'display']}" />
        <property name="template" title="Monitor Template" value="{xpf:array[@key = 'templates']/xpf:string[1]}" />
        <xsl:for-each select="xpf:array[@key = 'services']/xpf:string">
        <property name="service" title="Service Display Name" value="{.}" />
        </xsl:for-each>
    </properties-fragment>
</xsl:template>

</xsl:stylesheet>