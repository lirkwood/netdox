<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:template match="xpf:map[xpf:string[@key = 'type' and text() = 'Hardware Node']]">
    <xsl:param name="section" />
    <xsl:if test="$section = 'plugininf'">
        <section id="plugininf">

            <xsl:value-of select="xpf:string[@key = 'psml']" disable-output-escaping="yes"/>

            <properties-fragment id="origin">
                <property name="origin" title="Node Origin" datatype="xref">
                    <xref frag="default" uriid="{xpf:string[@key = 'origin_doc']}" />
                </property>
            </properties-fragment>

        </section>
    </xsl:if>
</xsl:template>

</xsl:stylesheet>