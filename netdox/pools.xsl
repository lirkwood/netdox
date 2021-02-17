<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

  <xsl:output method="xml" indent="yes" />
  <xsl:variable name="devices" select="json-to-xml(unparsed-text('src/devices.json'))"/>

  <!-- default template -->
  <xsl:template match="/">
      <xsl:variable name="pools" select="json-to-xml(pools)" />
      <xsl:apply-templates select="$pools//xpf:array/xpf:map" />
  </xsl:template>

  <xsl:template match="xpf:array/xpf:map">
    <xsl:variable name="uuid" select="xpf:string[@key='uuid']"/>
    <xsl:variable name="label" select="xpf:string[@key='name_label']"/>
    <xsl:result-document href="out/xo/{translate($label,'.','_')}.psml" method="xml" indent="yes">
      <document type="xo_pool" level="portable">
        <documentinfo>
          <uri title="{$label}" docid="_nd_{$uuid}"><labels>show-reversexrefs</labels></uri>
        </documentinfo>

        <metadata>
          <properties>
            <property name="template-version"     title="Template version"   value="1.2" />
          </properties>
        </metadata>
	
	      <section id="details">
        	<fragment id="title">
			      <heading level="1">Pool: <xsl:value-of select="$label" /></heading>
        	</fragment>
          <properties-fragment id="core">
            <property name="name-label"         title="Label"          value="{$label}" />
            <property name="name-description"   title="Description"              value="{xpf:string[@key='name_description']}" />
            <property name="uuid"               title="UUID"                     value="{$uuid}" />
          </properties-fragment>
    	  </section>

        <section id="members" title="Members">
          <xref-fragment id="xrefs">
            <xsl:if test="xpf:string[@key='master']">
              <blockxref type="embed" title="Controller" display="document+manual" docid="_nd_{xpf:string[@key='master']}" frag="default"
                    reverselink="true" reversetitle="Pool this device controls" reversetype="none" />
            </xsl:if>
            <xsl:for-each select="$devices//*[@key = $uuid]/xpf:string">
                <blockxref type="embed" title="Device" display="document+manual" docid="_nd_{.}" frag="default"
                      reverselink="true" reversetitle="Pool this device belongs to" reversetype="none" />
            </xsl:for-each>
          </xref-fragment>
        </section>

      </document>
    </xsl:result-document>
  </xsl:template>
</xsl:stylesheet>