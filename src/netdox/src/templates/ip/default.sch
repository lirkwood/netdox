<?xml version="1.0"?>
<!--
  This schematron validates a PSML document.

  The schematron rules can be used to enforce additional constraints required
  by the application.

  @see https://dev.pageseeder.com/api/psml.html
-->
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:title>Rules for IP documents</sch:title>
  
  <sch:pattern name="xref check">
    
    <sch:rule context="document">
      <sch:assert test="*//xref or documentinfo/reversexrefs" >Orphan</sch:assert>
    </sch:rule>
    
    <sch:rule context="//*[@unresolved]">
      <sch:assert test="@unresolved = 'false'">Unresolved link</sch:assert>
    </sch:rule>
    
  </sch:pattern>

</sch:schema>

