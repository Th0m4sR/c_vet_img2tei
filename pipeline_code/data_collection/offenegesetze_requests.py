import requests as rq
import io
from PyPDF2 import PdfReader, PdfWriter
import os
from regulation import Regulation, engine
from sqlalchemy.orm import Session


"""
Response keys:
count
next
previous
results
facets

Results:
id
kind
year
number
date
url
api_url
document_url
order
title
law_date
page
pdf_page
num_pages
title__highlight
content__highlight
score

The regulations are requested per year as all results are limited to at most 10 pages with at most 20 results on each
"""


def download_and_extract_pdf(url, start_page, end_page, output_path):
    # Download the PDF file
    response = rq.get(url)

    # Extract the specified range of pages
    input_pdf = PdfReader(io.BytesIO(response.content))
    output_pdf = PdfWriter()
    for page_number in range(start_page - 1, end_page):
        output_pdf.add_page(input_pdf.pages[page_number])

    # Save the extracted pages to a new PDF file
    with open(output_path, 'wb') as f:
        output_pdf.write(f)


def title_has_substring_from_list(substring_list, title):
    for substring in substring_list:
        if substring in title:
            return True
    return False


def query_and_store_regulations(query_string, start_year, end_year, output_dir, title_start_expression,
                                required_string_in_title_list=None):
    if required_string_in_title_list is None:
        required_string_in_title_list = list()
    results = []
    if start_year > end_year:
        raise ValueError(f"Start year ({start_year}) must be smaller than or equal to end year ({end_year})")
    for i in range(start_year, end_year + 1):
        url = f"https://api.offenegesetze.de/v1/veroeffentlichung/?q={query_string}&year={i}&kind=bgbl1&format=json"
        nxt = url
        first_it = True
        while nxt:
            api_response = rq.get(nxt)
            api_response_json = api_response.json()
            if first_it:
                print(f"Year: {i}. Results: {api_response_json['count']}")
                first_it = False
            nxt = api_response_json['next']
            for api_regulation in api_response_json['results']:
                # Check if it is an actual regulation
                if api_regulation['title'].startswith(title_start_expression):
                    # Get the required parameters for selecting the required pages from the PDF and how to name the PDF
                    url = api_regulation['document_url']
                    start_page = api_regulation['pdf_page']
                    end_page = api_regulation['pdf_page'] + api_regulation['num_pages'] - 1
                    title = api_regulation['title']
                    if not required_string_in_title_list or title_has_substring_from_list(required_string_in_title_list,
                                                                                          title):
                        reg = Regulation(id=api_regulation['id'],
                                         kind=api_regulation['kind'],
                                         year=api_regulation['year'],
                                         number=api_regulation['number'],
                                         date=api_regulation['date'],
                                         url=api_regulation['url'],
                                         api_url=api_regulation['api_url'],
                                         document_url=api_regulation['document_url'],
                                         order=api_regulation['order'],
                                         title=api_regulation['title'],
                                         law_date=api_regulation['law_date'],
                                         page=api_regulation['page'],
                                         pdf_page=api_regulation['pdf_page'],
                                         num_pages=api_regulation['num_pages'],
                                         score=api_regulation['score'])
                        reg.local_filename = str(abs(hash(reg))) + ".pdf"
                        file_name = reg.local_filename
                        results.append(f"{api_regulation['title']} - {api_regulation['year']}")
                        try:
                            output_path = os.path.join(output_dir, file_name)
                            download_and_extract_pdf(url, start_page, end_page, output_path)
                            with Session(engine) as session:
                                session.add(reg)
                                session.commit()
                        except Exception as e:
                            print(f"Error occurred when trying to download: {reg.title} - {reg.year}")
                            print(e)
                    else:
                        continue
    return results


def query_by_attribute(**kwargs):
    session = Session(engine)
    try:
        result = session.query(Regulation).filter_by(**kwargs).all()
        return result
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    start_year = 1949
    end_year = 2022

    # Query CVET regulations
    query_fulltext = "Fortbildungsordnung"
    out_dir = 'regulations/Offenegesetze/fortbildungsordnungen'
    regulations = query_and_store_regulations(query_fulltext, start_year, end_year, out_dir,
                                              title_start_expression='Verordnung über',
                                              required_string_in_title_list=['Meister', 'Fortbildung',
                                                                             'anerkannten Abschluss',
                                                                             'anerkannten Abschluß'])
    for r in regulations:
        print(r)
    print(f"Found regulations: {len(regulations)}")
    res_sum = 0
    for release_year in range(start_year, end_year):
        regulation_files = os.listdir(out_dir)
        year_dir = os.path.join(out_dir, str(release_year))
        results = query_by_attribute(year=release_year)
        if results is not None and len(results) > 0 and not os.path.isdir(year_dir):
            os.mkdir(year_dir)
        result_files = [reg.local_filename for reg in results]
        for file in result_files:
            source_path = os.path.join(out_dir, file)
            destination_path = os.path.join(year_dir, file)
            if file in regulation_files and file.endswith('.pdf'):
                res_sum += 1
                os.rename(source_path, destination_path)
    print(res_sum)

    # Query VET regulations
    query_fulltext = "Verordnung über die Berufsausbildung"
    out_dir = 'regulations/Offenegesetze/ausbildungsordnungen'
    regulations = query_and_store_regulations(query_fulltext, start_year, end_year, out_dir,
                                              title_start_expression='Verordnung über die Berufsausbildung',
                                              required_string_in_title_list=['die Berufsausbildung'])
    for r in regulations:
        print(r)
    print(f"Found regulations: {len(regulations)}")

    for release_year in range(start_year, end_year):
        regulation_files = os.listdir(out_dir)
        year_dir = os.path.join(out_dir, str(release_year))
        results = query_by_attribute(year=release_year)
        if results is not None and len(results) > 0 and not os.path.isdir(year_dir):
            os.mkdir(year_dir)
        result_files = [reg.local_filename for reg in results]
        for file in result_files:
            source_path = os.path.join(out_dir, file)
            destination_path = os.path.join(year_dir, file)
            if file in regulation_files and file.endswith('.pdf'):
                os.rename(source_path, destination_path)


