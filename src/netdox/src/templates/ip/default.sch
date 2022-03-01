<?xml version="1.0"?>
<!--
  This schematron validates a PSML document.

  The schematron rules can be used to enforce additional constraints required
  by the application.

  @see https://dev.pageseeder.com/api/psml.html
-->
<sch:schema 
  xmlns:sch="http://purl.oclc.org/dsdl/schematron" 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <sch:ns uri="http://netdox.allette.com.au/xslt-funcs" prefix="func" />

  
  <xsl:function name="func:parse-multiprop">
    <xsl:param name="property" />
    <xsl:variable name="returnval">
      <xsl:for-each select="$property/value/text()">
        <xsl:value-of select="concat(., ',')" />
      </xsl:for-each>
    </xsl:variable>
    <xsl:value-of select="$returnval" />
  </xsl:function>
  
  <sch:title>Rules for IP documents</sch:title>
  
  <sch:pattern name="XRef Check">
    
    <sch:rule context="document">
      <sch:assert test="*//xref or documentinfo/reversexrefs" >Orphan — no xrefs to or from this document.</sch:assert>
    </sch:rule>
    
  </sch:pattern>
  
  <sch:pattern name="Search Terms Check">
    
    <sch:rule context="document">
      
      <sch:let name="name"        value="./section[@id = 'header']/properties-fragment[@id = 'header']/property[@name = 'name']/@value" />
      <sch:let name="octet1"      value="substring-before($name, '.')" />
      <sch:let name="octets2_4"  value="substring-after($name, '.')" />
      <sch:let name="octet2"      value="substring-before($octets2_4, '.')" />
      <sch:let name="octets3_4"  value="substring-after($octets2_4, '.')" />
      <sch:let name="octet3"      value="substring-before($octets3_4, '.')" />
      <sch:let name="terms"       value="func:parse-multiprop(/document/section[@id = 'footer']/properties-fragment[@id = 'search']/property[@name = 'terms'])" />
      
      <sch:assert test="contains($terms, $octet4)"
        ><sch:value-of select="$octet4"/> not found in search terms.</sch:assert>
      <sch:assert test="contains($terms, $octets3_4)"
        ><sch:value-of select="$octets3_4"/> not found in search terms.</sch:assert>
    </sch:rule>
      
  </sch:pattern>

</sch:schema>