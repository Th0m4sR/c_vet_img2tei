from lxml import etree
from typing import Dict
from webapp_backend.data_access.exist_connector import query_regulation


NAMESPACES = {'x': 'http://www.w3.org/1999/xhtml',
              'y': 'http://exist.sourceforge.net/NS/exist',
              'v': 'http://exist-db.org/versioning'}

IMAGE_DIRECTORY = 'path/to/extracted/image_files'
IMAGE_URL = 'http://192.168.37.129:8000/uploads/'


def map_parameters_to_tei(parameters: Dict):
    # TODO Mehr Parameter hier aufnehmen
    if parameters is None:
        return {}
    tmp = {
        "*": parameters.get("text", None),
        "title": parameters.get("dokumententitel", None),
        "author/persName": parameters.get("author", None),
        "publPlace": parameters.get("erscheinungsort", None),
        "date": parameters.get("erscheinungsjahr", None)
    }
    result = {k: v for k, v in tmp.items() if v is not None}
    return result


def query_and_parse_regulations(regulation_query_params: Dict = None,
                                document_title: str = None,
                                version=None):
    result_regulations = query_regulation(map_parameters_to_tei(regulation_query_params),
                                          document_name=document_title,
                                          revision=version)
    results_tree = etree.fromstring(result_regulations)

    names = []
    documents = []
    revisions = []
    for document in results_tree:
        documents.append(document.xpath(".//TEI", namespaces=NAMESPACES)[0])
        names.append(document.xpath(".//name", namespaces=NAMESPACES)[0])
        document_revisions = []
        for revision in document.xpath(".//v:revisions", namespaces=NAMESPACES)[0]:
            new_rev = {
                'version': revision.attrib.get('rev'),
                'timestamp': revision.xpath(".//v:date", namespaces=NAMESPACES)[0].text,
                'user': revision.xpath(".//v:user", namespaces=NAMESPACES)[0].text
            }
            document_revisions.append(new_rev)
        revisions.append(document_revisions)

    results = [{'regulation': etree.tostring(documents[i], pretty_print=True, encoding='utf-8'),
                'title': documents[i].xpath(".//title", namespaces=NAMESPACES)[0].text,  # TODO Change to TEI namespace
                'time': documents[i].xpath(".//date", namespaces=NAMESPACES)[0].text if len(documents[i].xpath(
                    ".//date", namespaces=NAMESPACES)) > 0 else 0,
                # assumption: facs contains only one attribute in the pattern "image 'path/to/image'"
                'page_images': [IMAGE_URL + pb.attrib.get('facs').split("'")[1]
                                for pb in documents[i].xpath('.//pb', namespaces=NAMESPACES)],
                'exist_name': names[i].text.split("/")[-1],
                'revisions': revisions[i]}
               for i in range(len(results_tree))]
    return results
