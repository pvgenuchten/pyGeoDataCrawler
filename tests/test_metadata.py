from geodatacrawler.utils import parseDC, parseDataCite, parseISO, fetchMetadata

def test_parseDC():
    foo = parseDC({
        'name': 'faa',
        'datatype': 'raster',
        'geomtype': 'raster',
    },'faa')
    assert str(foo['mcf']['version']) == '1.0'
    assert foo['identification']['title'] == 'faa'

#def test_parseDatacite():
#    foo = parseDataCite({},'faa')
#    assert foo['mcf']['version'] == 1.0
#    assert foo['identification']['title'] == 'faa'

def test_parseISO():
    foo = parseISO('''<?xml version="1.0" encoding="UTF-8"?><gmd:MD_Metadata xsi:schemaLocation="http://www.isotc211.org/2005/gmd http://schemas.opengis.net/iso/19139/20060504/gmd/gmd.xsd" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gml="http://www.opengis.net/gml" xmlns:xlink="http://www.w3.org/1999/xlink">
<gmd:fileIdentifier><gco:CharacterString>366f6257-19eb-4f20-ba78-0698ac4aae77</gco:CharacterString></gmd:fileIdentifier>
<gmd:language><gmd:LanguageCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#LanguageCode" codeListValue="eng">eng</gmd:LanguageCode></gmd:language>
<gmd:hierarchyLevel><gmd:MD_ScopeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_ScopeCode" codeListValue="dataset">dataset</gmd:MD_ScopeCode></gmd:hierarchyLevel>
<gmd:contact><gmd:CI_ResponsibleParty><gmd:organisationName><gco:CharacterString>YPAAT</gco:CharacterString></gmd:organisationName><gmd:contactInfo><gmd:CI_Contact><gmd:address><gmd:CI_Address><gmd:electronicMailAddress><gco:CharacterString>ypaat@ypaat.gr</gco:CharacterString></gmd:electronicMailAddress></gmd:CI_Address></gmd:address></gmd:CI_Contact></gmd:contactInfo><gmd:role><gmd:CI_RoleCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_RoleCode" codeListValue="pointOfContact">pointOfContact</gmd:CI_RoleCode></gmd:role></gmd:CI_ResponsibleParty></gmd:contact>
<gmd:dateStamp><gco:Date>2009-10-09</gco:Date></gmd:dateStamp>
<gmd:metadataStandardName><gco:CharacterString>ISO19115</gco:CharacterString></gmd:metadataStandardName>
<gmd:metadataStandardVersion><gco:CharacterString>2003/Cor.1:2006</gco:CharacterString></gmd:metadataStandardVersion>
<gmd:identificationInfo><gmd:MD_DataIdentification><gmd:citation><gmd:CI_Citation>
<gmd:title><gco:CharacterString>Aerial Photos</gco:CharacterString></gmd:title>
<gmd:date><gmd:CI_Date><gmd:date><gco:Date>2009-10-09</gco:Date></gmd:date><gmd:dateType><gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_DateTypeCode" codeListValue="creation">creation</gmd:CI_DateTypeCode></gmd:dateType></gmd:CI_Date></gmd:date>
<gmd:identifier><gmd:RS_Identifier><gmd:code><gco:CharacterString>366f6257-19eb-4f20-ba78-0698ac4aae77</gco:CharacterString></gmd:code></gmd:RS_Identifier></gmd:identifier>
<gmd:identifier><gmd:RS_Identifier><gmd:code><gco:CharacterString>T_aerfo_RAS_1991_GR800P001800000012.tif</gco:CharacterString></gmd:code></gmd:RS_Identifier></gmd:identifier>
</gmd:CI_Citation></gmd:citation><gmd:abstract><gco:CharacterString>Aerial Photos</gco:CharacterString></gmd:abstract>
<gmd:pointOfContact><gmd:CI_ResponsibleParty><gmd:organisationName><gco:CharacterString>YPAAT</gco:CharacterString></gmd:organisationName><gmd:contactInfo><gmd:CI_Contact><gmd:address><gmd:CI_Address><gmd:electronicMailAddress><gco:CharacterString>ypaat@ypaat.gr</gco:CharacterString></gmd:electronicMailAddress></gmd:CI_Address></gmd:address></gmd:CI_Contact></gmd:contactInfo><gmd:role><gmd:CI_RoleCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_RoleCode" codeListValue="owner">owner</gmd:CI_RoleCode></gmd:role></gmd:CI_ResponsibleParty></gmd:pointOfContact>
<gmd:descriptiveKeywords><gmd:MD_Keywords><gmd:keyword><gco:CharacterString>Orthoimagery</gco:CharacterString></gmd:keyword><gmd:thesaurusName><gmd:CI_Citation><gmd:title><gco:CharacterString>GEMET - INSPIRE themes, version 1.0</gco:CharacterString></gmd:title><gmd:date><gmd:CI_Date><gmd:date><gco:Date>2008-06-01</gco:Date></gmd:date><gmd:dateType><gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_DateTypeCode" codeListValue="publication">publication</gmd:CI_DateTypeCode></gmd:dateType></gmd:CI_Date></gmd:date></gmd:CI_Citation></gmd:thesaurusName></gmd:MD_Keywords></gmd:descriptiveKeywords>
<gmd:resourceConstraints><gmd:MD_Constraints><gmd:useLimitation><gco:CharacterString>no conditions apply</gco:CharacterString></gmd:useLimitation></gmd:MD_Constraints></gmd:resourceConstraints>
<gmd:resourceConstraints><gmd:MD_LegalConstraints><gmd:accessConstraints><gmd:MD_RestrictionCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_RestrictionCode" codeListValue="otherRestrictions">otherRestrictions</gmd:MD_RestrictionCode></gmd:accessConstraints><gmd:otherConstraints><gco:CharacterString>no limitations</gco:CharacterString></gmd:otherConstraints></gmd:MD_LegalConstraints></gmd:resourceConstraints>
<gmd:language><gmd:LanguageCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#LanguageCode" codeListValue="eng">eng</gmd:LanguageCode></gmd:language>
<gmd:topicCategory><gmd:MD_TopicCategoryCode>geoscientificInformation</gmd:MD_TopicCategoryCode></gmd:topicCategory>
<gmd:extent><gmd:EX_Extent><gmd:geographicElement><gmd:EX_GeographicBoundingBox><gmd:westBoundLongitude><gco:Decimal>20.00</gco:Decimal></gmd:westBoundLongitude><gmd:eastBoundLongitude><gco:Decimal>24.00</gco:Decimal></gmd:eastBoundLongitude><gmd:southBoundLatitude><gco:Decimal>38.00</gco:Decimal></gmd:southBoundLatitude><gmd:northBoundLatitude><gco:Decimal>40.00</gco:Decimal></gmd:northBoundLatitude></gmd:EX_GeographicBoundingBox></gmd:geographicElement></gmd:EX_Extent></gmd:extent>
<gmd:extent><gmd:EX_Extent><gmd:temporalElement><gmd:EX_TemporalExtent><gmd:extent><gml:TimePeriod gml:id="ID_034c77cc-d473-4f5b-a7b2-8cc067031e21" xsi:type="gml:TimePeriodType"><gml:beginPosition>2009-10-09</gml:beginPosition><gml:endPosition>2009-10-09</gml:endPosition></gml:TimePeriod></gmd:extent></gmd:EX_TemporalExtent></gmd:temporalElement></gmd:EX_Extent></gmd:extent>
</gmd:MD_DataIdentification></gmd:identificationInfo><gmd:distributionInfo><gmd:MD_Distribution><gmd:distributionFormat><gmd:MD_Format><gmd:name gco:nilReason="inapplicable"/><gmd:version gco:nilReason="inapplicable"/></gmd:MD_Format></gmd:distributionFormat><gmd:transferOptions><gmd:MD_DigitalTransferOptions><gmd:onLine><gmd:CI_OnlineResource><gmd:linkage><gmd:URL>http://www.ypaat.gr</gmd:URL></gmd:linkage></gmd:CI_OnlineResource></gmd:onLine></gmd:MD_DigitalTransferOptions></gmd:transferOptions></gmd:MD_Distribution></gmd:distributionInfo></gmd:MD_Metadata>''','faa')
    assert str(foo['mcf']['version']) == '1.0'
    assert foo['identification']['title'] == 'Aerial Photos'