from lxml import etree
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict


# The URL to the eXist db server with collection and the elementtree
DB_URL = 'http://localhost:8080/exist/rest/{}/{}'
COLLECTION = 'playground'

# Defining the request headers
HEADERS = {'Content-Type': 'application/xml'}

# Adding basic HTTP authentication
username = 'admin'
password = 'admin'  # This needs to be adapted for the respective eXist-db

# Defining the Authentication header
AUTH = HTTPBasicAuth(username, password)

NAMESPACES = {'x': 'http://www.w3.org/1999/xhtml'}


def store_regulation(title, regulation_tree):
    """
    Creates or updates a regulation that is identified by its title
    :param title: Identifier of the regulation in the collection
    :param regulation_tree: The newly created or updated regulation
    :return: True if updating or creating was successful, False otherwise
    """
    xml_string = etree.tostring(regulation_tree, pretty_print=True, encoding='utf-8')
    request_url = DB_URL.format(COLLECTION, title)
    response = requests.put(request_url, data=bytes(xml_string), headers=HEADERS, auth=AUTH)
    if response.status_code != 201:
        # print('No item was created: %s; Code %s' % (response.text, response.status_code))
        return False
    else:
        # print("Ok.")
        return True


def query_regulation(element_substring_dict: Dict = None,
                     document_name=None,
                     revision=None):
    """
    Searches within the given collection if an element of a document contains the filter_value text
    :param element_substring_dict: XML-element to text mapping where the substring. To search in all elements,
    set the key to '*'. To search for any text in the element, set the value to ''
    :param document_name: name of the document in the database. If None, all documents are queried.
    :param revision: revision number that can be used to query the database
    :return: found regulation vet_files
    """
    # TODO Sanitize input to prevent code execution
    if element_substring_dict is None or len(element_substring_dict) == 0:
        element_substring_dict = {'*': ''}
    # TODO default namespace not yet implemented here

    filter_value_substring = '\nwhere' + '\nand'.join(
        [f' (some $item in $doc//{key} satisfies contains ($item, "{value}"))' for key, value in
         element_substring_dict.items()])

    if document_name is not None:
        filter_value_substring += f' and fn:contains(fn:base-uri($doc), "{document_name}")'

    if revision is None:
        doc_query_string = "{$doc}"
    else:
        doc_query_string = f"{{v:doc($doc, {revision})}}"

    xquery = f"""
    xquery version "3.1";
    import module namespace v="http://exist-db.org/versioning";
    let $collection := "/db/{COLLECTION}"
    for $doc in collection($collection)
    {filter_value_substring}
    return <document>
        <name>{{fn:base-uri($doc)}}</name>
        {doc_query_string}
        {{v:history($doc)}}
    </document>
    """
    # print(xquery)
    params = {
        "_how": "json",
        "_query": xquery,
    }
    response = requests.get(DB_URL, headers=HEADERS, params=params, auth=AUTH)
    if response.status_code == 200:
        return response.text  # This will contain the result XML
    else:
        raise ValueError(f"Something went wrong executing xquery:\nError: {response.text}\n"
                         f"Code: {response.status_code}\nxquery: {xquery}")


def delete_database_elements(title):
    request_url = DB_URL.format(COLLECTION, title)
    response = requests.delete(request_url, headers=HEADERS, auth=AUTH)
    if response.status_code == 200:
        return True
    else:
        return False


# delete_database_elements('')
# root = etree.parse('../_tei_examples/brd_holzbearbeitungsmechaniker_1980.xml')
# store_regulation('testing1', root)
# root = etree.parse('../_tei_examples/brd_fachkraft_küche_2022.xml')
# store_regulation('testing2', root)

# res = query_regulation({'*': ''})  # , 'p': 'a'
# print(res)
