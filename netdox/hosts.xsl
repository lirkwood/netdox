<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

  <xsl:output method="xml" indent="yes" />
  <xsl:variable name="vms" select="json-to-xml(unparsed-text('src/residents.json'))"/>

  <!-- default template -->
  <xsl:template match="/">
      <xsl:variable name="hosts" select="json-to-xml(hosts)" />
      <xsl:apply-templates select="$hosts//xpf:array/xpf:map" />
  </xsl:template>

  <xsl:template match="xpf:array/xpf:map">
    <xsl:variable name="uuid" select="xpf:string[@key='uuid']"/>
    <xsl:variable name="label" select="xpf:string[@key='name_label']"/>
    <xsl:result-document href="out/xo/{translate($label,'.','_')}.psml" method="xml" indent="yes">
      <document type="xo_host" level="portable">
        <documentinfo>
          <uri title="xo_host: {$label}" docid="_nd_{$uuid}"><labels>show-reversexrefs</labels></uri>
        </documentinfo>

        <metadata>
          <properties>
            <property name="template-version"     title="Template version"   value="2.0" />
          </properties>
        </metadata>

        <section id="title">
        	<fragment id="title">
			      <heading level="1"><xsl:value-of select="$label" /></heading>
        	</fragment>
        </section>
	
        <section id="details">
          <properties-fragment id="core">
            <property name="name-label"         title="Label"          value="{$label}" />
            <property name="name-description"   title="Description"              value="{xpf:string[@key='name_description']}" />
            <property name="uuid"               title="UUID"                     value="{xpf:string[@key='uuid']}" />
          </properties-fragment>
          <properties-fragment id="addresses">
            <property name="host"          title="Host name"                value="{xpf:string[@key='hostname']}" />
            <property name="ipv4"       title="Internal IP"             datatype="xref" >
              <xref frag="default" docid="{concat('_nd_', translate(xpf:string[@key='address'], '.', '_'))}"
              reversetitle="{$label} in XO" />
	          </property>
	          <property name="subnet" title="Subnet" value="{xpf:string[@key = 'subnet']}" />
          </properties-fragment>
          <properties-fragment id="cpus">
            <property name="host-cpu-count"          title="CPU count"      value="{xpf:map[@key='CPUs']/xpf:string[@key='cpu_count']}" />
            <property name="host-cpu-socket-count"   title="CPU sockets"    value="{xpf:map[@key='CPUs']/xpf:string[@key='socket_count']}" />
            <property name="host-cpu-vendor"         title="CPU vendor"     value="{xpf:map[@key='CPUs']/xpf:string[@key='vendor']}" />
            <property name="host-cpu-speed"          title="CPU speed"      value="{xpf:map[@key='CPUs']/xpf:string[@key='speed']}" />
            <property name="host-cpu-modelname"      title="CPU model"      value="{xpf:map[@key='CPUs']/xpf:string[@key='modelname']}" />
          </properties-fragment>
          <properties-fragment id="location">
            <property name="pool"            title="Pool"           datatype="xref">
              <xsl:if test="xpf:string[@key='$pool']">
                <xref type="none" display="document" docid="_nd_{xpf:string[@key='$pool']}" frag="default"
                      reverselink="true" reversetitle="Hosts in this pool" reversetype="none" />
              </xsl:if>
            </property>
          </properties-fragment>
          <properties-fragment id="status">
            <property name="power-state"        title="Power state"    value="{xpf:string[@key='power_state']}"/>
          </properties-fragment>
        </section>

        <section id="vms" title="VMs">
          <xref-fragment id="xrefs">
            <xsl:for-each select="$vms//*[@key = $uuid]/xpf:string">
                <blockxref type="embed" docid="_nd_{.}" frag="default"
                      reverselink="true" reversetitle="Host of this VM" reversetype="none" />
            </xsl:for-each>
          </xref-fragment>
        </section>

      </document>
    </xsl:result-document>
  </xsl:template>
</xsl:stylesheet>
