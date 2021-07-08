<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:outxsl="http://allette.com.au/netdox/metaxslt"
                exclude-result-prefixes="">

<xsl:output method="xml" omit-xml-declaration="yes"/>

<xsl:namespace-alias stylesheet-prefix="outxsl" result-prefix="xsl" />

<xsl:template match="/">
    <xsl:variable name="workers" select="json-to-xml(root)/xpf:map/xpf:map"/>
    <outxsl:stylesheet version="3.0"
            xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
            xmlns:xpf="http://www.w3.org/2005/xpath-functions"
            exclude-result-prefixes="#all" >
    <xsl:copy select="." />
    <xsl:copy-of select="@*"/>
    <xsl:for-each select="$workers/xpf:array">

            <outxsl:template match="xpf:map[xpf:string[@key='docid' and text()='{@key}']]">
                <outxsl:param name="section" />
                <outxsl:if test="$section = 'other'">

                    <xref-fragment id="k8sapps">
                        <xsl:for-each select="xpf:string">
                            <blockxref type="embed" frag="default" docid="{.}" />
                        </xsl:for-each>
                    </xref-fragment>

                </outxsl:if>
            </outxsl:template>

    </xsl:for-each>
    </outxsl:stylesheet>
</xsl:template>

</xsl:stylesheet>