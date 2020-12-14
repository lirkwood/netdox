<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="3.0" 
xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
xmlns:js="http://www.w3.org/2005/xpath-functions">
 <xsl:variable name="main" select="/"/>
 <xsl:variable name="json" select="json-to-xml(unparsed-text('../../Sources/Ansible/desired.json'))"/>

 <xsl:output method="xml" indent="yes"/>
 
<!-- [@key = 'ato2.allette.com.au'] -->

<xsl:template match="/">
    <xsl:for-each select="child::*/child::*">
        <xsl:variable name="host" select="@key"/>
        <xsl:variable name="docid">
            <xsl:choose>
            <xsl:when test="contains($host, '.internal')">
                <xsl:value-of select="concat('_nd_', translate(substring-before($host, '.internal'), '.', '_'))"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="concat('_nd_', translate($host, '.', '_'))"/>
            </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <!-- removing the .internal and formatting the hostname to be docid compliant -->
        <xsl:result-document href="raw/{$docid}.psml">
            <xsl:element name="document">
                <xsl:for-each select="$json/*/*">
                <!-- for every parent listed in desired.json -->
                <xsl:variable name="parent" select="@key"/>
                    <!-- encode fragment id in filename for convenience -->
                    <xsl:element name="properties-fragment">
                        <xsl:attribute name="id" select="$parent"/>
                        <xsl:for-each select="child::*">
                            <xsl:variable name="key" select="."/>
                            <!-- store value of key if it is a string -->
                            <xsl:choose>
                                <xsl:when test="self::js:string">
                                    <xsl:apply-templates select="$main//*[@key = $host]//*[@key = $parent]/js:string">
                                    <!-- apply template on all nodes that have the right host, parent, and are strings -->
                                        <xsl:with-param name="parent" select="$parent"/>
                                        <xsl:with-param name="key" select="$key"/>
                                    </xsl:apply-templates>
                                </xsl:when>
                                <xsl:otherwise>
                                    <xsl:apply-templates select="$main//*[@key = $host]//*[@key = $parent]/js:map">
                                        <xsl:with-param name="parent" select="$parent"/>
                                        <xsl:with-param name="key" select="$key"/>
                                    </xsl:apply-templates>
                                    <!-- pass node instead of string content for richer info -->
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:for-each>
                    </xsl:element>
                    <!-- <xsl:message select='concat($host, " fragment ", $parent, " prcoessed.")' /> -->
                </xsl:for-each>
            </xsl:element>
        </xsl:result-document>
    </xsl:for-each>
</xsl:template>

<xsl:template match="js:string">
    <xsl:param name="key" />
    <xsl:param name="parent" />
    <xsl:variable name="keytext">
        <xsl:value-of select="$key" />
    </xsl:variable>
    <xsl:variable name="hierarchy">
        <xsl:for-each select="ancestor::*">
            <xsl:value-of select="concat(';', @key, ';')" />
        </xsl:for-each>
    </xsl:variable>
    <xsl:choose>
        <xsl:when test="@key = $keytext">
            <xsl:element name="property">
                <xsl:attribute name="name" select="concat('_ans_', $hierarchy, @key, ';')"/>
                <xsl:attribute name="title" select="translate(concat($parent, ' ', @key), '_', ' ')"/>
                <xsl:attribute name="value" select="."/>
            </xsl:element>
        </xsl:when>
        <xsl:when test="$keytext = 'all'">
        <!-- used for getting all values out of arrays -->
            <xsl:element name="property">
                <xsl:attribute name="name" select="concat('_ans_', $hierarchy)"/>
                <xsl:attribute name="title" select="translate(concat($parent, ' ', @key), '_', ' ')"/>
                <xsl:attribute name="value" select="."/>
            </xsl:element>
        </xsl:when>
    </xsl:choose>
</xsl:template>

<xsl:template match="js:map">
    <xsl:param name="key" />
    <xsl:choose>
        <xsl:when test="name($key) = 'array'">
        <!-- if we are tying to match on an array -->
            <xsl:variable name="node" select="."/>
            <!-- store current context node so we know what we tried to match on the array with -->
            <xsl:for-each select="$key/child::*">
                <!-- next pass match on the children of the array -->
                <xsl:variable name="newkey" select="text()"/>
                <!-- store key again -->
                <xsl:choose>
                    <!-- begin matching as in root template -->
                    <xsl:when test="self::js:string = 'all'">
                        <xsl:if test="$node/@key = $key/@key">
                            <xsl:apply-templates select="$node/*">
                                <xsl:with-param name="parent" select="$node/@key"/>
                                <xsl:with-param name="key" select="$newkey"/>
                            </xsl:apply-templates>
                        </xsl:if>
                    </xsl:when>
                    <xsl:when test="self::js:string != 'all'">
                        <xsl:if test="$node/@key = $key/@key or not($key/@key)">
                        <!-- if matching specific key or searching all objs -->
                            <xsl:apply-templates select="$node/child::*[@key = $newkey]">
                                <xsl:with-param name="parent" select="$node/@key"/>
                                <xsl:with-param name="key" select="$newkey"/>
                            </xsl:apply-templates>
                        </xsl:if>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:apply-templates select="$node/child::*">
                            <xsl:with-param name="parent" select="$node/@key"/>
                            <xsl:with-param name="key" select="."/>
                        </xsl:apply-templates>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:for-each>
        </xsl:when>
        <xsl:when test="name($key) = 'map'">
        <!-- if we are trying to match on a dict -->
            <xsl:variable name="node" select="."/>
            <xsl:for-each select="$key/child::*">
            <!-- for each key in the dict -->
                <xsl:variable name="newkey" select="."/>
                <xsl:choose>
                    <xsl:when test="$node/@key = $newkey/@key">
                    <!-- test if the currently matched node has the same name -->
                        <xsl:apply-templates select="$node/child::*">
                            <xsl:with-param name="parent" select="$node/@key"/>
                            <xsl:with-param name="key" select="$newkey"/>
                        </xsl:apply-templates>
                        <!-- if it does, match as normal for a non string obj, as dict need not be
                        used unless you are specifying another dict or an array -->
                    </xsl:when>
                </xsl:choose>
            </xsl:for-each>
        </xsl:when>
    </xsl:choose>
</xsl:template>
 
</xsl:stylesheet>