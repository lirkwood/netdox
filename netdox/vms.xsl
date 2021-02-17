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
    <xsl:result-document href="out/vms/{xpf:string[@key='name_label']}.psml" method="xml" indent="yes">
      <document type="xo_vm" level="portable">
        <documentinfo>
          <uri title="vm: {xpf:string[@key='name_label']}" docid="_nd_{xpf:string[@key='uuid']}"><labels>show-reversexrefs</labels></uri>
        </documentinfo>

        <metadata>
          <properties>
            <property name="template-version"     title="Template version"   value="1.1" />
          </properties>
        </metadata>
	
        <section id="title">
        	<fragment id="title">
            <heading level="1">vm: <xsl:value-of select="xpf:string[@key='name_label']" /></heading>
        	</fragment>
        </section>

        <section id="details" title="details">
          <properties-fragment id="core">
            <property name="name-label"         title="Label"          value="{xpf:string[@key='name_label']}" />
            <property name="name-description"   title="Description"   value="{xpf:string[@key='name_description']}" />
            <property name="uuid"               title="UUID"          value="{xpf:string[@key='uuid']}" />
          </properties-fragment>
          <properties-fragment id="addresses">
            <property name="ipv4"               title="IPv4"          datatype="xref" >
              <xref frag="default" docid="_nd_{translate(xpf:map[@key='addresses']/xpf:string[@key='0/ipv4/0'], '.', '_')}"
              reversetitle="{xpf:string[@key='name_label']} in XO" />
            </property>
	    <property name="subnet" title="Subnet" value="{xpf:string[@key = 'subnet']}" />
            <property name="ipv6"               title="IPv6"          value="{xpf:map[@key='addresses']/xpf:string[@key='0/ipv6/0']}" />
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
                <xref type="none" display="document" docid="_nd_{xpf:string[@key='$container']}" frag="default"
                      reverselink="true" reversetitle="VMs on this host" reversetype="none" />
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