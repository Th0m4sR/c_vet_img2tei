from bs4 import BeautifulSoup
import requests as rq


"""
This module is used to find all apprenticeships on the website of bibb and download the PDF-vet_files that contain the
regulations of each apprenticeship
"""


def request_apprenticeships_pages():
    """
    The website of bibb has a page where all apprenticeships starting with a certain letter are sorted:
    https://www.bibb.de/dienst/berufesuche/de/index_berufesuche.php/alphabetical/apprenticeship/a
    This page is requested to find all pages that contain references to each apprenticeship.
    Once all these pages are found, they are requested to find the pages that refer to apprenticeships.
    A list of these pages is returned
    :return: A list of pages of apprenticeships that contain the regulation documents for these apprenticeships
    """
    # On this website, all apprenticeships are listed alphabetically
    joblist_url = "https://www.bibb.de/dienst/berufesuche/de/index_berufesuche.php/alphabetical/apprenticeship/a"

    # This stores all possible letters in the ordering of the bibb-website where the jobs are sorted
    all_letter_apprenticeships = []
    # Here the links to the page of each apprenticeship is stored
    apprenticeships = []

    # First, all letters to request are stored to then be requested
    result = rq.get(joblist_url)
    # Now we filter to find all pages where apprenticeships are listed
    soup = BeautifulSoup(result.content, "html.parser")
    for link in soup.find_all('a'):
        href = link.get('href')
        if href is None:
            continue
        if "/dienst/berufesuche/de/index_berufesuche.php/alphabetical/apprenticeship/" in href:
            all_letter_apprenticeships.append("https://www.bibb.de" + href)

    # As we now know where to find apprenticeships, we request each page
    for url in all_letter_apprenticeships:
        print(f"Requesting: {url}")
        result = rq.get(url)
        soup = BeautifulSoup(result.content, "html.parser")
        for link in soup.find_all('a'):
            href = link.get('href')
            if href is None:
                continue
            if "www.bibb.de/dienst/berufesuche/de/index_berufesuche.php/profile/apprenticeship/" in href:
                apprenticeships.append(href)

    print(f"Status: {result.status_code}")
    print(f"Found {len(apprenticeships)} results")
    return apprenticeships


def find_pdf_link(page):
    """
    Finds the link to the regulation document on the input page and returns it
    :param page: The page about an apprenticeship that refers to the regulation of the apprenticeships
    :return: The link to the download of the regulation
    """
    result = rq.get(page)
    soup = BeautifulSoup(result.content, "html.parser")
    for link in soup.find_all('a'):
        href = link.get('href')
        if href is None:
            continue
        if "https://www.bibb.de/dienst/berufesuche/de/index_berufesuche.php/regulation/" in href:
            return href
    raise ValueError(f"Could not find a link to a regulation on page {page}")


def download_pdf(url):
    """
    Downloads a PDF that is located under the input URL
    :param url: URL of the PDF-document
    :return:
    """
    result = rq.get(url)
    if result.headers.get('content-type') != "application/pdf":
        raise ValueError("The input URL does not contain a PDF-file")
    with open("regulations/" + url.split("/")[-1], 'wb') as file:
        file.write(result.content)


if __name__ == "__main__":
    apprenticeship_pages = request_apprenticeships_pages()
    pdf_urls = []
    count = 0
    for page in apprenticeship_pages:
        count += 1
        try:
            pdf_urls.append(find_pdf_link(page))
        except ValueError as e:
            print(e)
        if count == 1 or count % 25 == 0:
            print(f"Crawled {count} of {len(pdf_urls)} pages")
    count = 0
    for pdf in pdf_urls:
        count += 1
        download_pdf(pdf)
        if count == 1 or count % 25 == 0:
            print(f"Downloaded {count} of {len(apprenticeship_pages)} PDF vet_files")
