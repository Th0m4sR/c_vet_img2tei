NAMESPACES = {'x': 'http://www.w3.org/1999/xhtml'}
TEMP_WORKSPACE_ROOT_DIR = '/tmp/'
LOG_DIRECTORY = 'data_directory/logs/vet'
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
EMPTY_HOCR_TREE = """
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
 </head>
 <body>
  <div class='ocr_page'>
  </div>
 </body>
</html>
"""
EMPTY_TEI_HEADER = """
<teiHeader>
 <fileDesc>
  <titleStmt>
   <title></title>
   <author>
    <persName></persName>
    <orgName></orgName>
   </author>
  </titleStmt>
  <publicationStmt>
   <publisher/>
   <pubPlace></pubPlace>
   <date></date>
  </publicationStmt>
  <sourceDesc>
   <p/>
  </sourceDesc>
 </fileDesc>
</teiHeader>
"""