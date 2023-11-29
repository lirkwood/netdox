EBS_VOLUME_TEMPLATE = '''
    <document type="aws_volume" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <documentinfo>
            <uri docid="#!docid" title="#!id">
                <labels />
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="1.0" />
            </properties>
        </metadata>

        <section id="title" lockstructure="true">
            <fragment id="title">
                <heading level="2">EBS Volume</heading>
                <heading level="1">#!id</heading>     
            </fragment>
        </section>
        
        <section id="details" lockstructure="true">

            <properties-fragment id="details">
                <property name="volumeId"   title="Volume ID"   value="#!id" />
                <property name="size"       title="Size (GiB)"  value="#!size" />
                <property name="type"       title="Volume Type" value="#!type" />
                <property name="created"    title="Created"     value="#!created" />
                <property name="multi_attach"   title="Multi Attach Allowed"   value="#!multi_attach" />
            </properties-fragment>

        </section>

    </document>
'''

SECURITY_GROUP_TEMPLATE = '''
    <document type="aws_security_group" level="portable" xmlns:t="http://pageseeder.com/psml/template">

        <documentinfo>
            <uri docid="#!docid" title="#!group_name">
                <labels />
            </uri>
        </documentinfo>

        <metadata>
            <properties>
                <property name="template_version"     title="Template version"   value="1.0" />
            </properties>
        </metadata>

        <section id="title" lockstructure="true">
            <fragment id="title">
                <heading level="1">#!group_name</heading>
            </fragment>
        </section>

        <section id="details" lockstructure="true">

            <properties-fragment id="details">
                <property name="group_id"   title="Group ID"   value="#!group_id" />
                <property name="group_name"   title="Group Name"   value="#!group_name" />
                <property name="description"   title="Description"   value="#!description" />
                <property name="owner_id"   title="Owner ID"   value="#!owner_id" />
                <property name="vpc_id"   title="VPC ID"   value="#!vpc_id" />
            </properties-fragment>

            <properties-fragment id="tags" />

        </section>

        <section id="ip_ingress" lockstructure="true" />

        <section id="ip_egress" lockstructure="true" />

    </document>
'''
