<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

  <xsl:output method="xml" indent="yes" />

  <!-- default template -->
  <xsl:template match="/">
      <xsl:variable name="vms" select="json-to-xml(vms)" />
      <xsl:apply-templates select="$vms//xpf:array/xpf:map" />
  </xsl:template>

  <xsl:template match="xpf:array/xpf:map">
    <xsl:result-document href="out/xo/{xpf:string[@key='name_label']}.psml" method="xml" indent="yes">
      <document type="xo_vm" level="portable">

        <xsl:variable name="labels">
            <xsl:choose>
              <xsl:when test="xpf:string[@key='power_state'] = 'Halted'">,xo_halted</xsl:when>
              <xsl:when test="xpf:string[@key='power_state'] = 'Suspended'">,xo_suspended</xsl:when>
              <xsl:when test="xpf:string[@key='power_state'] = 'Running'">,xo_running</xsl:when>
            </xsl:choose>
        </xsl:variable>

        <documentinfo>
          <uri title="xo_vm: {xpf:string[@key='name_label']}" docid="_nd_{xpf:string[@key='uuid']}">
            <labels>show-reversexrefs<xsl:value-of select="$labels"/></labels>
          </uri>
        </documentinfo>

        <metadata>
          <properties>
            <property name="template-version"     title="Template version"   value="2.0" />
          </properties>
        </metadata>
	
        <section id="title">
        	<fragment id="title">
            <heading level="2">Xen Orchestra VM</heading>
            <heading level="1"><xsl:value-of select="xpf:string[@key='name_label']" /></heading>
        	</fragment>
        </section>

        <section id="details" title="details">
          <properties-fragment id="core">
            <property name="name-label"         title="Label"          value="{xpf:string[@key='name_label']}" />
            <property name="name-description"   title="Description"   value="{xpf:string[@key='name_description']}" />
            <property name="uuid"               title="UUID"          value="{xpf:string[@key='uuid']}" />
            <xsl:for-each select="xpf:array[@key = 'domains']/xpf:string">
              <property name="domain" title="Domain" datatype="xref">
                <xref frag="default" docid="_nd_{translate(.,'.','_')}"
                reversetitle="VM exposed by this domain"/>
              </property>
            </xsl:for-each>
          </properties-fragment>
          <properties-fragment id="addresses">
            <property name="ipv4"               title="IPv4"          datatype="xref" >
            <xsl:if test="xpf:string[@key='mainIpAddress']">
              <xref frag="default" docid="_nd_{translate(xpf:string[@key='mainIpAddress'], '.', '_')}" reversetitle="{xpf:string[@key='name_label']} in XO" />
            </xsl:if>
            </property>
            <property name="subnet" title="Subnet" value="{xpf:string[@key = 'subnet']}" />
          </properties-fragment>
          <properties-fragment id="os_version">
            <property name="os-name"            title="OS name"        value="{xpf:map[@key='os_version']/xpf:string[@key='name']}" />
            <property name="os-uname"           title="OS uname"       value="{xpf:map[@key='os_version']/xpf:string[@key='uname']}" />
            <property name="os-distro"          title="Distro"         value="{xpf:map[@key='os_version']/xpf:string[@key='distro']}" />
            <property name="os-major"           title="Major version"  value="{xpf:map[@key='os_version']/xpf:string[@key='major']}" />
            <property name="os-minor"           title="Minor version"  value="{xpf:map[@key='os_version']/xpf:string[@key='minor']}" />
          </properties-fragment>
          <properties-fragment id="location">
            <property name="xen_host"       title="Host machine"           datatype="xref">
              <xsl:if test="xpf:string[@key='$container']">
                <xsl:choose>
                  <xsl:when test="xpf:string[@key='power_state'] = 'Running'">
                <xref type="none" display="document" docid="_nd_{xpf:string[@key='$container']}" frag="default"
                      reverselink="true" reversetitle="VMs on this host" reversetype="none" />
                  </xsl:when>
                  <xsl:otherwise>
                <xref type="none" display="document" docid="_nd_{xpf:string[@key='$container']}" frag="default"
                      reverselink="true" reversetitle="Halted/Suspended VMs in this pool" reversetype="none" />
                  </xsl:otherwise>
                </xsl:choose>
              </xsl:if>
            </property>
            <property name="xen_pool"            title="Pool"           datatype="xref">
              <xsl:if test="xpf:string[@key='$pool']">
                <xref type="none" display="document" docid="_nd_{xpf:string[@key='$pool']}" frag="default"
                      reverselink="true" reversetitle="VMs in this pool" reversetype="none" />
              </xsl:if>
            </property>
          </properties-fragment>
          <properties-fragment id="status">
            <property name="power-state"        title="Power state"    value="{xpf:string[@key='power_state']}"/>
          </properties-fragment>

        </section>
      </document>
    </xsl:result-document>
  </xsl:template>
</xsl:stylesheet>