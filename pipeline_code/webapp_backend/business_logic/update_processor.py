from lxml import etree
from webapp_backend.data_access import exist_connector
import traceback


# TODO Ein Schema, damit alle nötigen Sachen vorhanden sind, wäre gut
def update_regulation(exist_name: str, xml_string):
    try:
        updated_regulation = etree.fromstring(xml_string)
        title = exist_name.split("/")[-1].strip()
        return exist_connector.store_regulation(title=title, regulation_tree=updated_regulation)
    except etree.XMLSyntaxError as e:
        print(traceback.format_exc())
        return False
