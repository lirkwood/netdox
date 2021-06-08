<?xml version="1.0"?>
<!--
  This schematron validates a PSML document.

  The schematron rules can be used to enforce additional constraints required
  by the application.

  @see https://dev.pageseeder.com/api/psml.html
-->
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:title>Rules for IP documents</sch:title>

  <sch:let name="subnetlist" value="'103.127.18.0/26,103.127.18.64/26,103.127.18.128/25,192.168.2.0/25,192.168.2.128/26,192.168.2.192/27,192.168.2.224/28,192.168.2.240/30,192.168.2.244/30,192.168.2.252/30,192.168.4.0/25,192.168.4.128/26,192.168.5.0/24,192.168.6.0/24,192.168.7.0/24,192.168.8.0/23,192.168.10.0/23,192.168.10.0/24,192.168.11.0/24,192.168.12.0/24,192.168.12.0/24,192.168.13.0/24,192.168.14.0/23,192.168.200.0/24'"/>
  
  <sch:pattern name="subnet check">
    
    <sch:rule context="*//property[(@name='subnet') and (starts-with(@value, '192.168.') or starts-with(@value, '103.127.18.'))]">
    
      <sch:assert test="contains($subnetlist, @value)" >Bad subnet <sch:value-of select="@value" /></sch:assert>
    
    </sch:rule>
    
  </sch:pattern>
  
  <sch:pattern name="xref check">
    
    <sch:rule context="document">
      <sch:assert test="*//xref or documentinfo/reversexrefs" >Orphan</sch:assert>
    </sch:rule>
    
  </sch:pattern>

</sch:schema>

