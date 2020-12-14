<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
 <xsl:output indent="yes" omit-xml-declaration="no"/>
 <xsl:variable name="json" select="unparsed-text('../../Sources/Ansible/ansible.json')"/>
 <xsl:template match="/">
  <xsl:copy-of select="json-to-xml($json)"/>
 </xsl:template>
</xsl:stylesheet>