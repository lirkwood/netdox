<xsl:stylesheet version="3.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xpf="http://www.w3.org/2005/xpath-functions"
                exclude-result-prefixes="#all">

<xsl:template match="xpf:map[xpf:string[@key='type' and text()='AWS EC2 Instance']]">

    <section id="plugininf">

        <properties-fragment id="instanceinf">
            <property name="name"               title="Name"                value="{xpf:string[@key='name']}"/>
            <property name="instanceId"         title="Instance Id"         value="{xpf:string[@key='id']}"/>
            <property name="mac"                title="MAC Address"         value="{xpf:string[@key='mac']}"/>
            <property name="instanceType"       title="Instance Type"       value="{xpf:string[@key='instance_type']}"/>
            <property name="monitoring"         title="Monitoring"          value="{xpf:string[@key='monitoring']}" />
            <property name="availabilityZone"   title="Availability Zone"   value="{xpf:string[@key='region']}"/>
        </properties-fragment>

        <properties-fragment id="tags">
            <xsl:for-each select="xpf:map[@key = 'tags']/xpf:string">
                <property name="tag" title="{@key}" value="{.}" />
            </xsl:for-each>
        </properties-fragment>
    
    </section>

</xsl:template>

</xsl:stylesheet>
