<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:template match="xpf:map[xpf:string[@key = 'type' and text() = 'XenOrchestra VM']]">
      <section id="plugininf">
        <properties-fragment id="core">
          <property name="name-label"         title="Label"          value="{xpf:string[@key='name']}" />
          <property name="name-description"   title="Description"   value="{xpf:string[@key='desc']}" />
          <property name="uuid"               title="UUID"          value="{xpf:string[@key='uuid']}" />
          <property name="xen_host"       title="Host machine"           datatype="xref">
              <xref type="none" display="document" docid="_nd_node_xohost_{xpf:string[@key='host']}" frag="default"
                    reverselink="true" reversetitle="VMs on this host" reversetype="none" />
          </property>
        </properties-fragment>
        <properties-fragment id="os_version">
          <property name="template"           title="Template"       value="{xpf:map[@key='template']/xpf:string[@key='base_template_name']}" />
          <property name="os-name"            title="OS name"        value="{xpf:map[@key='os']/xpf:string[@key='name']}" />
          <property name="os-uname"           title="OS uname"       value="{xpf:map[@key='os']/xpf:string[@key='uname']}" />
          <property name="os-distro"          title="Distro"         value="{xpf:map[@key='os']/xpf:string[@key='distro']}" />
          <property name="os-major"           title="Major version"  value="{xpf:map[@key='os']/xpf:string[@key='major']}" />
          <property name="os-minor"           title="Minor version"  value="{xpf:map[@key='os']/xpf:string[@key='minor']}" />
        </properties-fragment>

      </section>
  </xsl:template>

</xsl:stylesheet>