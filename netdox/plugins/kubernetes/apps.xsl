<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-errors"
                exclude-result-prefixes="#all">

<xsl:output method="xml" indent="yes" />

<xsl:template match="/">
    <xsl:variable name="apps" select="json-to-xml(apps)"/>
    <xsl:for-each select="$apps/xpf:map/xpf:map">
        <xsl:apply-templates select="xpf:map">
            <xsl:with-param name="context" select="@key"/>
        </xsl:apply-templates>
    </xsl:for-each>
</xsl:template>

<xsl:template match="xpf:map">
    <xsl:param name="context"/>
    <xsl:try>
        <xsl:result-document href="out/k8s/{$context}/{@key}.psml">
            <document level="portable" type="k8s_app">

                <documentinfo>
                    <uri title="k8s_app: {@key}" docid="_nd_{@key}" />
                </documentinfo>

                <metadata>
                    <properties>
                        <property name="template_version" title="Template version" value="2.1" />
                    </properties>
                </metadata>
    
                <section id="title">
                    <fragment id="title">
                        <heading level="1"><xsl:value-of select="@key"/></heading>
                    </fragment>
                </section>
                
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

                <properties-fragment id="domains">
                    <xsl:for-each select="xpf:array[@key = 'domains']/xpf:string">
                        <property name="domain" title="Domain" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(.,'.','_')}" 
                            reversetitle="App served on this domain" />
                        </property>
                    </xsl:for-each>
                </properties-fragment>

                </section>

                <section id="pods" title="Running Pods">

                    <xsl:for-each select="xpf:map[@key = 'pods']/xpf:map">
                    <properties-fragment id="pod_{position()}">
                        <property name="pod"  title="Pod"  value="{@key}" />
                        <property name="ipv4"  title="Worker IP"  datatype="xref" >
                            <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'hostip'],'.','_')}" 
                                reversetitle="App running on this IP" />
                        </property>
                        <xsl:if test="xpf:string[@key = 'vm']">
                        <property name="worker_vm" title="Worker VM" datatype="xref" >
                            <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'vm'],'.','_')}"
                            reversetitle="App running on this VM"/>
                        </property>
                        </xsl:if>
                        <property name="rancher" title="Pod on Rancher" datatype="link">
                            <link href="{xpf:string[@key = 'rancher']}"><xsl:value-of select="@key"/> on rancher.</link>
                        </property>
                    </properties-fragment>
                    </xsl:for-each>
                
                </section>
            </document>
        </xsl:result-document>
        <xsl:catch>
            <xsl:message>[ERROR][apps.xsl] The transformation threw an exception.
            [ERROR][apps.xsl] Error code: <xsl:value-of select="$err:code"/>
            [ERROR][apps.xsl] Error description: <xsl:value-of select="$err:description"/>
            [ERROR][apps.xsl] ****END****</xsl:message>
        </xsl:catch>
    </xsl:try>
</xsl:template>

</xsl:stylesheet>