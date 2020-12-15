<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="3.0" 
xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:variable name="main" select="/"/>
<xsl:output method="xml" indent="yes"/>

<xsl:template match="/">
    <xsl:element name="document">
      <xsl:apply-templates select="*//properties-fragment"/>
    </xsl:element>
</xsl:template>

<xsl:template match="properties-fragment">
  <xsl:variable name="fragment">
    <xsl:value-of select="@id" />
  </xsl:variable>
  <xsl:variable name="filename" select="tokenize(document-uri($main), '/')[count(tokenize(document-uri($main), '/'))]"/>
  <xsl:variable name="docid" select="tokenize($filename, '.psml')[1]"/>
  <xsl:choose>
    <xsl:when test="$fragment = 'ansible_devices'">
      <xsl:for-each select="child::*[contains(@name, 'uuid')]">
      <!-- group by uuid -->
        <xsl:variable name="name" select="tokenize(@name, ';')[10]" />
        <xsl:variable name="newfrag" select="concat($fragment, '_', $name)"/>
        <xsl:result-document href="{$docid};{$newfrag};.psml">
          <xsl:element name="properties-fragment">
            <xsl:attribute name="id" select="$fragment"/>
            <xsl:element name="property" >
              <xsl:attribute name="name" select="'device_name'"/>
              <xsl:attribute name="title" select="'Device Name'"/>
              <xsl:attribute name="value" select="$name"/>
            </xsl:element>
            <!-- new fragment for each device with a uuid -->
            <!-- this purposefully groups partitions as most devices only have one uuid -->
            <xsl:apply-templates select="../*[contains(@name, concat(';', $name, ';'))]">
              <xsl:with-param name="fragment" select="$fragment"/>
            </xsl:apply-templates>
          </xsl:element>
        </xsl:result-document>
      </xsl:for-each>
    </xsl:when>
    <xsl:when test="$fragment = 'ansible_mounts'">
      <xsl:for-each select="child::*[contains(@name, 'uuid')]">
        <xsl:variable name="id" select="tokenize(@title, ' ')[1]"/>
        <xsl:variable name="uuid" select="@value"/>
        <xsl:variable name="mountname">
          <xsl:choose>
            <xsl:when test="string-length($uuid) > 4">
              <xsl:choose>
                <xsl:when test="contains($main//*[@id = 'ansible_devices']/*[@value = $uuid]/@name, 'partitions')">
                  <xsl:value-of select="tokenize($main//*[@id = 'ansible_devices']/*[@value = $uuid]/@name, ';')[14]" />
                </xsl:when>
                <!-- match on device with same uuid -->
                <xsl:otherwise>
                  <xsl:value-of select="tokenize($main//*[@id = 'ansible_devices']/*[@value = $uuid]/@name, ';')[10]" />
                </xsl:otherwise>
              </xsl:choose>
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of select="$id" />
            </xsl:otherwise>
          </xsl:choose>
        </xsl:variable>
        <xsl:variable name="newfrag" select="concat($fragment, '_', $mountname)"/>
        <xsl:result-document href="{$docid};{$newfrag};.psml">
          <xsl:element name="properties-fragment">
            <xsl:attribute name="id" select="$fragment"/>
            <xsl:element name="property" >
              <xsl:attribute name="name" select="'mount_name'"/>
              <xsl:attribute name="title" select="'Mount Name'"/>
              <xsl:attribute name="value" select="$mountname"/>
            </xsl:element>
            <xsl:apply-templates select="parent::*/child::*[contains(@name, $id)]">
              <xsl:with-param name="fragment" select="$fragment"/>
            </xsl:apply-templates>
          </xsl:element>
        </xsl:result-document>
      </xsl:for-each>
    </xsl:when>
    <xsl:otherwise>
      <xsl:result-document href="{$docid};{$fragment};.psml">
        <xsl:element name="properties-fragment">
          <xsl:attribute name="id" select="$fragment"/>
          <xsl:element name="property" >
            <xsl:attribute name="name" select="'fragment_name'"/>
            <xsl:attribute name="title" select="'Fragment Name'"/>
            <xsl:attribute name="value" select="$fragment"/>
          </xsl:element>
          <xsl:apply-templates select="child::*"/>
        </xsl:element>
      </xsl:result-document>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="property">
  <xsl:variable name="hierarchy" select="@name"/>
  <xsl:variable name="title" select="tokenize($hierarchy, ';')[count(tokenize($hierarchy, ';')) - 1]"/>
  <xsl:copy>
    <xsl:copy-of select="@*"/>
    <xsl:attribute name="name" select="$title"/>
    <xsl:attribute name="title" select="$title"/>
  </xsl:copy>
</xsl:template>

</xsl:stylesheet>