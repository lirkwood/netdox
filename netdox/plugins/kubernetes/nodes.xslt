<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:template match="xpf:map[xpf:string[@key = 'type' and text() = 'Kubernetes App']]">
    <section id="template" title="Pod Template">

    <xsl:for-each select="xpf:map[@key = 'template']/xpf:map">
        <properties-fragment id="container_{position()}">
            <property name="container" title="Container Name" value="{@key}" />
            <property name="image" title="Image ID" value="{xpf:string[@key = 'image']}" />
            <xsl:for-each select="xpf:map[@key = 'volumes']/xpf:map">
                <property name="pvc" title="Persistent Volume Claim" value="{@key}" />
                <property name="mount_path" title="Path in Container" value="{xpf:string[@key = 'mount_path']}" />
                <property name="sub_path" title="Path in PVC" value="{xpf:string[@key = 'sub_path']}" />
            </xsl:for-each>
        </properties-fragment>
    </xsl:for-each>

    </section>
    
    <section id="pods" title="Running Pods">

        <xsl:for-each select="xpf:map[@key = 'pods']/xpf:map">
        <properties-fragment id="pod_{position()}">
            <property name="pod"  title="Pod"  value="{@key}" />
            <property name="ipv4"  title="Worker IP"  datatype="xref" >
                <xref frag="default" docid="_nd_ip_{translate(xpf:string[@key = 'hostip'],'.','_')}" 
                    reversetitle="App running on this IP" />
            </property>
            <xsl:if test="xpf:string[@key = 'vm']">
            <property name="worker_vm" title="Worker VM" datatype="xref" >
                <xref frag="default" docid="_nd_node_xovm_{translate(xpf:string[@key = 'vm'],'.','_')}"
                reversetitle="App running on this VM"/>
            </property>
            </xsl:if>
            <property name="rancher" title="Pod on Rancher" datatype="link">
                <link href="{xpf:string[@key = 'rancher']}"><xsl:value-of select="@key"/> on rancher.</link>
            </property>
        </properties-fragment>
        </xsl:for-each>
    
    </section>
</xsl:template>

</xsl:stylesheet>