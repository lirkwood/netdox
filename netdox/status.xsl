<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="review" select="json-to-xml(review)"/>
    <xsl:variable name="date" select="format-date(current-date(), '[Y0001]-[M01]-[D01]')"/>
    <xsl:variable name="dateTime" select="format-dateTime(adjust-dateTime-to-timezone(current-dateTime(), xs:dayTimeDuration('PT10H')), '[Y0001]-[M01]-[D01] at [H01]:[m01] [z]')"/>
<document level="portable">
    <documentinfo>
        <uri title="Status Update" docid="_nd_status_update"><labels>show-reversexrefs</labels></uri>
    </documentinfo>
    <section id="title">
        <fragment id="title">
            <heading level="1">Status Update on <xsl:value-of select="$dateTime"/></heading>
        </fragment>
        <properties-fragment id="stats">
            <property name="total" title="No. of domains up for review" value="{count($review//xpf:string)}" />
            <property name="imgdiff" title="No. of sites that look different today" value="{count($review//xpf:string[. = 'imgdiff'])}" />
            <property name="no_base" title="No. of sites which did not have a base image" value="{count($review//xpf:string[. = 'no_base'])}" />
            <property name="no_ss" title="No. of sites Puppeteer failed to screenshot" value="{count($review//xpf:string[contains(.,'no_ss')])}" />
        </properties-fragment>
    </section>
    <section id="imgdiff">
        <fragment id="imgdiff_title">
            <heading level="2">Sites that look different today</heading>
        </fragment>
    <xsl:for-each select="$review/xpf:map/xpf:string[. = 'imgdiff']">
        <properties-fragment id="imgdiff_{position()}_xref">
            <property name="page" title="Webpage DNS Record" datatype="xref">
                <xref frag="default" reversetitle="Status Update" docid="_nd_{translate(@key, '.', '_')}" />
            </property>
        </properties-fragment>
        <fragment id="imgdiff_{position()}_img_col1" labels="text-align-center,col-1-of-2">
            <block label="border-2">
                <para>Expected screenshot</para>
                <image src="/ps/operations/network/website/screenshot_history/{$date}/{translate(@key, '.', '_')}.jpg"/>
            </block>
        </fragment>
        <fragment id="imgdiff_{position()}_img_col2" labels="text-align-center,col-1-of-2">
            <block label="border-2">
                <para>Actual screenshot</para>
                <image src="/ps/operations/network/website/screenshots/{translate(@key, '.', '_')}.jpg"/>
            </block>
        </fragment>
        <fragment id="imgdiff_{position()}_img_diff" labels="text-align-center">
            <block label="border-2">
                <para>Expected screenshot with diff overlay</para>
                <image src="/ps/operations/network/website/review/{translate(@key, '.', '_')}.jpg"/>
            </block>
        </fragment>
    </xsl:for-each>
    </section>
    <section id="no_base">
        <fragment id="nose_base_title">
            <heading level="2">Sites with no base image</heading>
        </fragment>
    <xsl:for-each select="$review/xpf:map/xpf:string[. = 'no_base']">
        <properties-fragment id="no_base_{position()}_xref">
            <property name="page" title="Webpage DNS Record" datatype="xref">
                <xref frag="default" reversetitle="Status Update" docid="_nd_{translate(@key, '.', '_')}" />
            </property>
        </properties-fragment>
        <fragment id="no_base_{position()}_img" labels="text-align-center">
            <block label="border-2">
                <image src="/ps/operations/network/website/screenshots/{translate(@key, '.', '_')}.jpg"/>
            </block>
        </fragment>
    </xsl:for-each>
    </section>
    <section id="no_ss">
        <fragment id="nose_ss_title">
            <heading level="2">Sites Puppeteer failed to screenshot</heading>
        </fragment>
    <xsl:for-each select="$review/xpf:map/xpf:string[substring-before(., ':') = 'no_ss']">
        <properties-fragment id="no_ss_{position()}">
            <property name="page" title="Webpage DNS Record" datatype="xref">
                <xref frag="default" reversetitle="Status Update" docid="_nd_{translate(@key, '.', '_')}" />
            </property>
        </properties-fragment>
    </xsl:for-each>
    </section>
</document>
</xsl:template>

</xsl:stylesheet>