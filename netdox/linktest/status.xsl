<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
<document level="portable">
    <documentinfo>
        <uri title="Status Update" docid="_nd_status_update"><labels>show-reversexrefs</labels></uri>
    </documentinfo>
    <section id="title">
        <fragment id="title">
            <heading level="1">Status Update on <xsl:value-of select="format-dateTime(current-dateTime(), '[Y0001]-[M01]-[D01] at [H01]:[m01] [z]')"/></heading>
        </fragment>
        <properties-fragment id="stats">
            <property name="total" title="No. of domains up for review" value="{count(json-to-xml(root)//xpf:string)}" />
            <property name="imgdiff" title="No. of screenshots which did not match base image" value="{count(json-to-xml(root)//xpf:string[. = 'imgdiff'])}" />
            <property name="no_base" title="No. of domains which did not have a base image" value="{count(json-to-xml(root)//xpf:string[. = 'no_base'])}" />
            <property name="no_ss" title="No. of domains Puppeteer failed to screenshot" value="{count(json-to-xml(root)//xpf:string[contains(.,'no_ss')])}" />
        </properties-fragment>
    </section>
    <section id="review" title="Pages for Review">
    <xsl:for-each select="json-to-xml(root)/xpf:map/xpf:string">
        <properties-fragment id="{position()}_xref">
            <property name="page" title="Webpage DNS Record" datatype="xref">
                <xref frag="default" reversetitle="Status Update" docid="{substring-before(concat(substring-before(@key, 'img_'),substring-after(@key, 'img_')),'.png')}" />
            </property>
        <xsl:choose>
            <xsl:when test=". = 'imgdiff'">
                    <property name="reason" title="Reason for review" value="Differences found between screenshot and base image." />
            </xsl:when>
            <xsl:when test=". = 'no_base'">
                    <property name="reason" title="Reason for review" value="No base image for odiff to compare to." />
            </xsl:when>
            <xsl:when test="substring-before(.,':') = 'no_ss'">
                    <property name="reason" title="Reason for review" value="Puppeteer failed to take a screenshot due to an error: '{substring-after(.,':')}'" />
            </xsl:when>
        </xsl:choose>
        </properties-fragment>
        <xsl:choose>
            <xsl:when test=". = 'imgdiff'">
        <fragment id="{position()}_img_col1" labels="text-align-center, col-1-of-2">
            <block label="border-2">
                <image src="/ps/network/documentation/website/review/{@key}"/>
            </block>
        </fragment>
        <fragment id="{position()}_img_col2" labels="text-align-center, col-1-of-2">
            <block label="border-2">
                <image src="/ps/network/documentation/website/screenshots/{@key}"/>
            </block>
        </fragment>
            </xsl:when>
            <xsl:when test=". = 'no_base'">
        <fragment id="{position()}_img" labels="text-align-center">
            <block label="border-2">
                <image src="/ps/network/documentation/website/review/{@key}"/>
            </block>
        </fragment>
            </xsl:when>
        </xsl:choose>
    </xsl:for-each>
    </section>
</document>
</xsl:template>

</xsl:stylesheet>