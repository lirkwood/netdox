<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                xmlns:err="http://www.w3.org/2005/xqt-error"
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
    <xsl:try>
        <xsl:result-document href="out/k8s/{@key}.psml">
            <document level="portable" type="k8s_app">

                <documentinfo>
                    <uri title="app: {@key}" docid="_nd_{@key}" />
                </documentinfo>

                <metadata>
                    <properties>
                        <property name="template_version" title="Template version" value="1.0" />
                    </properties>
                </metadata>
    
                <section id="title">
                    <fragment id="title">
                        <heading level="1">app: <xsl:value-of select="@key"/></heading>
                    </fragment>
                </section>
                
                <section id="details" title="Details">

                    <properties-fragment id="kube_pods">
                        <xsl:for-each select="xpf:map[@key = 'pods']/xpf:map">
                            <property name="pod"  title="Pod"  value="{@key}" />
                            <xsl:for-each select="xpf:map[@key = 'containers']/xpf:string">
                                <property name="container" title="Container" value="{@key}" />
                                <property name="image" title="Image ID" value="{.}"/>
                            </xsl:for-each>
                        </xsl:for-each>
                    </properties-fragment>
                    
                    <properties-fragment id="kube_worker">
                        <property name="worker_vm" title="Worker VM" datatype="xref" >
                            <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'vm'],'.','_')}"
                            reversetitle="App running on this VM"/>
                        </property>
                        <property name="worker_hostname" title="Worker Hostname" datatype="xref">
                            <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'worker'],'.','_')}"  
                                reversetitle="App running on this worker"/>
                        </property>
                        <property name="ipv4"  title="Worker IP"  datatype="xref" >
                            <xref frag="default" docid="_nd_{translate(xpf:string[@key = 'hostip'],'.','_')}" 
                                reversetitle="App running on this IP" />
                        </property>
                    </properties-fragment>
                    
                    <properties-fragment id="domains">
                        <xsl:for-each select="xpf:array[@key = 'domains']/xpf:string">
                            <property name="domain" title="Domain" datatype="xref">
                                <xref frag="default" docid="_nd_{translate(.,'.','_')}" 
                                reversetitle="App served on this domain" />
                            </property>
                        </xsl:for-each>
                    </properties-fragment>
                    
                    <fragment id="links">
                    <xsl:for-each select="*//xpf:map[@key = 'containers']/xpf:string">
                        <xsl:if test="contains(.,'registry-gitlab.allette.com.au')">
                        <para><link href="{substring-before(substring-after(.,'registry-'),':')}">Project on GitLab.</link></para>
                        </xsl:if>
                    </xsl:for-each>
                    <xsl:for-each select="xpf:map[@key = 'pods']/xpf:map">
                        <para><link href="{xpf:string[@key = 'rancher']}">Pod <xsl:value-of select="@key"/> on Rancher.</link></para>
                    </xsl:for-each>
                    </fragment>
                
                </section>
            </document>
        </xsl:result-document>
        <xsl:catch>
            <xsl:message>[ERROR][apps.xsl] The transformation threw an exception.</xsl:message>
            <xsl:message>[ERROR][apps.xsl] Error code: <xsl:value-of select="$err:code"/></xsl:message>
            <xsl:message>[ERROR][apps.xsl] Error description: <xsl:value-of select="$err:description"/></xsl:message>
            <xsl:message>[ERROR][apps.xsl] ****END****</xsl:message>
        </xsl:catch>
    </xsl:try>
</xsl:template>

</xsl:stylesheet>