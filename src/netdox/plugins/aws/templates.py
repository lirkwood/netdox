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