from webapp_backend.data_access.exist_connector import delete_database_elements


def delete_regulation(regulation_name: str):
    return delete_database_elements(regulation_name)
