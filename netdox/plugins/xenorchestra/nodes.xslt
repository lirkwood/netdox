<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:template match="xpf:map[xpf:string[@key = 'type' and text() = 'XenOrchestra VM']]">
    <section id="plugininf">

        <properties-fragment id="core">
            <property name="description"        title="Description"    value="{xpf:string[@key='desc']}" />
            <property name="uuid"               title="UUID"           value="{xpf:string[@key='uuid']}" />
            <property name="xen_host"           title="Host machine"   datatype="xref">
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

<xsl:template match="xpf:map[xpf:string[@key = 'type' and text() = 'XenOrchestra Host']]">
    <section id="plugininf">

        <properties-fragment id="core">
            <property name="name-description"   title="Description"              value="{xpf:string[@key='desc']}" />
            <property name="uuid"               title="UUID"                     value="{xpf:string[@key='uuid']}" />
            <property name="pool"               title="Pool"                     value="{xpf:string[@key='pool']}" />
        </properties-fragment>

        <properties-fragment id="cpus">
            <property name="host-cpu-count"          title="CPU count"      value="{xpf:map[@key='CPUs']/xpf:string[@key='cpu_count']}" />
            <property name="host-cpu-socket-count"   title="CPU sockets"    value="{xpf:map[@key='CPUs']/xpf:string[@key='socket_count']}" />
            <property name="host-cpu-vendor"         title="CPU vendor"     value="{xpf:map[@key='CPUs']/xpf:string[@key='vendor']}" />
            <property name="host-cpu-speed"          title="CPU speed"      value="{xpf:map[@key='CPUs']/xpf:string[@key='speed']}" />
            <property name="host-cpu-modelname"      title="CPU model"      value="{xpf:map[@key='CPUs']/xpf:string[@key='modelname']}" />
        </properties-fragment>

        <xref-fragment id="xrefs">
            <xsl:for-each select="xpf:array[@key = 'vms']/xpf:string">
                <blockxref type="embed" docid="_nd_node_xovm_{.}" frag="default"
                            reverselink="true" reversetitle="Host of this VM" reversetype="none" />
            </xsl:for-each>
        </xref-fragment>
    </section>
</xsl:template>
    
</xsl:stylesheet>