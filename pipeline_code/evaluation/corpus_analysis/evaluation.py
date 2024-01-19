from lxml import etree
import structure_analysis
import word_analysis
import tei_tools
import json
import os


"""
This module is used to call the evaluation functions. These are for now:
- How often is each layout type found in VET (CVET respectively)?
- How many teile, abschnitte, paragraphen are in general in each regulation?
- How often do nestings become how deep (i.e., first, second, third, fourth level and so on)?
- How many pages do the regulations have (words)?
- How does all this evolve over time? (For that, I should store results per year and then accumulate or so)
- What are the most common headlines in VET (CVET respectively)?
- Which parts become longer / shorter (Count lines or words in paragraph and map them to the headlines).
    Then compare headlines and merge (Levenshtein Distance; again do everything over time / per year)?
    -> First, get most common clusters  <- LAST TODO
- How does the vocabulary change over time (word count -> Filter for substantives and so and filter:
                                                        - Which are only in one regulation?
                                                        - Are some of them no longer used over time?)?
                                                    -> pandas um Ergebnisse zu speichern
"""


"""
For each regulation create this structure:

{
    'title': 'Verordnung über die Berufsausbildung',
    'year': '2023',
    'text_structure': {
        'teil': [
            {
                'headline': 'Teil 1 Überschrift',
                'lines': 100,
                'words': 10000,
            },
            {
                'headline': 'Teil 2 Überschrift',
                'lines': 100,
                'words': 10000,
            }
        ],
        'abschnitt': [
            {
                'headline': 'Abschnitt 1 Gegenstand, Dauer und Gliederung',
                'lines': 100,
                'words': 10000,
            },
            {
                'headline': 'Abschnitt 2 Zwischenprüfung',
                'lines': 100,
                'words': 10000,
            }
        ],
        'paragraph': [
            {
                'headline': '§ 1 Staatliche Anerkennung'
                'lines': 100,
                'words': 10000,
            }
        ]
    },
    'deepest_text_nesting': 6,
    'page_count': 42,
}
"""

"""
{
    'year': 2023
    'title: 'Verordnung über die Berufsausbildung'
    'word_counts': { 
        'word': 'count
    }
}
"""

# IMPORTANT: HEADLINES ARE EXCLUDED FROM LINES!


def analyze_regulation_structure(regulation_tree: etree.ElementTree):
    result_dict = {
        'title': tei_tools.get_document_title(regulation_tree),
        'year': tei_tools.get_document_year(regulation_tree),
        'text_structure': structure_analysis.detect_text_structure(regulation_tree),
        'deepest_text_nesting': structure_analysis.get_deepest_nesting(regulation_tree),
        'page_count': structure_analysis.count_pages(regulation_tree)
    }
    json_result = json.dumps(result_dict, indent=4, ensure_ascii=False)
    return json_result


def analyze_regulation_text(regulation_tree: etree.ElementTree):
    result_dict = {
        'title': tei_tools.get_document_title(regulation_tree),
        'year': tei_tools.get_document_year(regulation_tree),
        'word_counts': word_analysis.count_p_words(regulation_tree)
    }
    json_result = json.dumps(result_dict, indent=4, ensure_ascii=False)
    return json_result


tei_directory = 'data_directory/tei_output/cvet/'
# out_dir = 'data_directory/evaluation/cvet/structure'
out_dir = 'data_directory/evaluation/cvet/word_counts'

for tei_file in os.listdir(tei_directory):
    tei_path = os.path.join(tei_directory, tei_file)
    tree = etree.parse(tei_path)
    out_path = os.path.join(out_dir, os.path.splitext(tei_file)[0] + ".json")
    # json_result = analyze_regulation_structure(tree)
    json_result = analyze_regulation_text(tree)
    # print(json_result)
    with open(out_path, 'w', encoding='utf-8') as file:
        file.write(json_result)


# regulation_file_path = 'data_directory/tei_output/vet/brd_fachkraft_küche_2022.xml'
# tree = etree.parse(regulation_file_path)
# print(analyze_regulation_text(tree))
# print(etree.tostring(tree, pretty_print=True, encoding='unicode'))
