import json
import os.path
from typing import List, Dict
import matplotlib.pyplot as plt
from matplotlib import ticker
from Levenshtein import distance
from collections import Counter
import numpy as np
from nltk.corpus import stopwords
import string
from sklearn.cluster import DBSCAN
import psycopg2
import re
import spacy
import enchant


data_collection_db_url = 'postgresql+psycopg2://postgres:thomas@localhost:5432/masterthesis'
conn = psycopg2.connect(
    dbname='masterthesis',
    user='postgres',
    password='postgres',
    host='localhost',
    port='5432'
)


# - Compare which / how many titles were missing
def compare_regulation_titles(structure_dicts: List[Dict],
                              query: str = "SELECT title FROM public.regulation WHERE title LIKE 'Verordnung über die Berufsausbildung%'",  # For vet: LIKE statt NOT LIKE
                              show_plot: bool = False,
                              plot_path: str = None):
    # test_str.translate(str.maketrans('', '', string.punctuation))
    detected_titles = [re.sub(r'[^\w\d\s]', '', " ".join(sad['title'].split("\n"))) for sad in structure_dicts]
    detected_titles.sort()
    # Query the database that contains the regulation infos
    db_connection = psycopg2.connect(
        dbname='masterthesis',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5432'
    )
    cursor = db_connection.cursor()

    cursor.execute(query)
    result_rows = cursor.fetchall()
    actual_titles = [re.sub(r'[^\w\d\s]', '', result_row[0]) for result_row in result_rows]
    actual_titles.sort()

    actual_titles_remains = actual_titles.copy()
    detected_titles_remains = detected_titles.copy()

    print(f"Detected: {len(detected_titles)}")
    print(f"Actual: {len(actual_titles)}")

    detected_idx = 0
    while detected_idx < len(detected_titles_remains):
        actual_idx = 0
        while actual_idx < len(actual_titles_remains):
            detected_title = detected_titles_remains[detected_idx]
            actual_title = actual_titles_remains[actual_idx]
            if distance(detected_title, actual_title) <= 8:
                detected_titles_remains.remove(detected_title)
                actual_titles_remains.remove(actual_title)
                detected_idx -= 1  # This resets the detected_idx since the last one was removed
                break
            actual_idx += 1
        detected_idx += 1

    print(f"Detected Remains: {len(detected_titles_remains)}")
    print(f"Actual Remains: {len(actual_titles_remains)}")

    print(f"Detected Remains: {detected_titles_remains}")
    print(f"Actual Remains: {actual_titles_remains}")

    cursor.close()
    db_connection.close()

    return {'actual_remains': actual_titles_remains,
            'detected_remains': detected_titles_remains}


# - Compare how many years have been correctly detected
def compare_regulations_per_year(structure_dicts: List[Dict],
                                 query: str = "SELECT year FROM public.regulation WHERE title LIKE 'Verordnung über die Berufsausbildung%'",  # For cvet: NOT LIKE statt LIKE
                                 show_plot: bool = False,
                                 plot_path: str = None):

    detected_years = [sad['year'] for sad in structure_dicts]
    # Query the database that contains the regulation infos
    db_connection = psycopg2.connect(
        dbname='masterthesis',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5432'
    )
    cursor = db_connection.cursor()
    cursor.execute(query)
    result_rows = cursor.fetchall()
    actual_years = [result_row[0] for result_row in result_rows]
    cursor.close()
    db_connection.close()

    if show_plot or plot_path is not None:
        all_years = detected_years + actual_years
        min_year = min(all_years)
        max_year = max(all_years)
        bins = [year - 0.5 for year in range(min_year, max_year + 2)]
        plt.hist([detected_years, actual_years], bins=bins, label=['Digitized regulations', 'Actual regulations'],
                 align='mid', alpha=0.7)
        plt.xlabel('Years')
        plt.ylabel('Number of regulations in year')
        plt.title('Frequency of years in data sets')
        plt.legend()
        plt.locator_params(axis='y', integer=True)
        plt.grid(axis='y')

        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        plt.clf()
        plt.close('all')
    return {'detected': detected_years, 'actual': actual_years}


# - How often is each layout type found in VET (CVET respectively)?
def count_layout_types(structure_dicts: List[Dict],
                       show_plot: bool = False,
                       plot_path: str = None) -> Dict[str, int]:
    """
    Finds all layout types and counts how often each one occurs
    :param structure_dicts:
    :param show_plot:
    :param plot_path:
    :return:
    """
    # Get all layout types
    layout_types = []
    for sad in structure_dicts:
        type_string = ''
        for elemen_type, properties in sad['text_structure'].items():
            if len(properties) > 0:
                type_string += elemen_type + " "
        layout_types.append(type_string.strip())
    # Count how often each layout type is present
    layout_type_counts = {}
    for layout_type in set(layout_types):
        layout_type_counts[layout_type] = layout_types.count(layout_type)

    if show_plot or plot_path is not None:
        layouts = list(layout_type_counts.keys())
        counts = list(layout_type_counts.values())
        plt.figure(figsize=(14, 9))
        plt.pie(counts, labels=None, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title('Occurrences of Layout Type')
        plt.legend(layouts, title='Text layouts', loc='upper left')
        plt.tight_layout()
        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        plt.clf()
        plt.close('all')
    return layout_type_counts


# - How many teile, abschnitte, paragraphen are in general in each regulation?
# -> Histogram
def count_text_elements(structure_dicts: List[Dict],
                        show_plot: bool = False,
                        plot_path: str = None) -> Dict[str, List[int]]:
    """
    Counts how often each possible text element occurs (teil, abschnitt, paragraph)
    :param structure_dicts:
    :param show_plot:
    :param plot_path:
    :return:
    """
    text_element_counts = {}
    for sad in structure_dicts:
        text_elements = sad['text_structure']
        for element_type, properties in text_elements.items():
            if element_type not in text_element_counts.keys():
                text_element_counts[element_type] = []
            text_element_counts[element_type].append(len(properties))

    if show_plot or plot_path is not None:
        num_plots = len(text_element_counts)
        num_cols = 2
        num_rows = (num_plots + num_cols - 1) // num_cols
        fig, axs = plt.subplots(num_rows, num_cols, figsize=(10, 8))
        if num_rows > 1:
            axs = axs.flatten()
        for i, (key, value) in enumerate(text_element_counts.items()):
            ax = axs[i] if num_plots > 1 else axs

            ax.hist(value, bins=30)
            ax.set_title(key)
            ax.set_xlabel('Counts')
            ax.locator_params(axis='y', integer=True)
            if max(value) <= 50:
                ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
            elif max(value) <= 100:
                ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
        plt.tight_layout()
        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        fig.clf()
        plt.close('all')
    return text_element_counts


# - How often do nestings become how deep (i.e., first, second, third, fourth level and so on)?
# -> Histogram

def count_document_nesting_level(structure_dicts: List[Dict],
                                 show_plot: bool = False,
                                 plot_path: str = None) -> Dict[int, int]:
    """
    Counts how often which nesting in a text element is the deepest level
    :param structure_dicts:
    :param show_plot:
    :param plot_path:
    :return:
    """
    text_nesting_counts = {}
    for sad in structure_dicts:
        deepest_nesting = sad['deepest_text_nesting']
        text_nesting_counts[deepest_nesting] = text_nesting_counts.get(deepest_nesting, 0) + 1

    for i in range(max(text_nesting_counts.keys())):
        if i not in text_nesting_counts.keys():
            text_nesting_counts[i] = 0

    if show_plot or plot_path is not None:
        fig, ax = plt.subplots(figsize=(12, 8))
        keys = list(text_nesting_counts.keys())
        frequencies = [text_nesting_counts[key] for key in keys]
        ax.bar([k for k in text_nesting_counts.keys()], [v for v in text_nesting_counts.values()])
        ax.set_xlabel('Text Nesting Level')
        ax.set_ylabel('Frequency')
        ax.set_title('Frequency distribution of deepest text nestings')
        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        fig.clf()
        plt.close('all')
    return text_nesting_counts


# - How does the length of the regulations differ between earlier and later versions of the regulations?
# -> box plot for evolution over time (page count only?)
def count_pages_over_time(structure_dicts: List[Dict],
                          show_plot: bool = False,
                          plot_path: str = None) -> Dict[int, List[int]]:
    """
    Counts how many pages were in a regulation in each year
    :param structure_dicts:
    :param show_plot:
    :param plot_path:
    :return:
    """
    year_to_page_counts = {}
    for sad in structure_dicts:
        year = sad['year']
        if year < 1970 or year > 2023:
            continue
        page_count = sad['page_count']
        if year not in year_to_page_counts.keys():
            year_to_page_counts[year] = []
        year_to_page_counts[year].append(page_count)

    if show_plot or plot_path is not None:
        years = list(year_to_page_counts.keys())

        box_plot_data = [year_to_page_counts[year] for year in years]

        fig, ax1 = plt.subplots(1, 1, figsize=(8, 6))
        ax1.boxplot(box_plot_data, positions=years, widths=0.6, patch_artist=True)
        ax1.set_ylabel('Page count')
        ax1.set_title('Page count distribution over multiple years')
        ax1.set_xticks(years)
        ax1.set_xticklabels(years, rotation='vertical')
        ax1.grid(True)
        ax1.set_ylim(bottom=0)

        plt.tight_layout()

        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        fig.clf()
        plt.close('all')
    return year_to_page_counts


# - How many pages do the regulations have (words)?
# -> Histogram
def count_page_distribution(structure_dicts: List[Dict],
                            show_plot: bool = False,
                            plot_path: str = None) -> List[int]:
    """
    Gets the distribution of page counts of all regulations
    :param structure_dicts:
    :param show_plot:
    :param plot_path:
    :return:
    """
    page_counts = []
    for sad in structure_dicts:
        page_counts.append(sad['page_count'])
    if show_plot or plot_path is not None:
        plt.hist(page_counts, bins=len(set(page_counts)))
        plt.xlabel('Number of pages')
        plt.ylabel('Frequency')
        plt.title('Distribution of page counts')
        plt.grid(True)
        plt.margins(x=0)

        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        plt.clf()
        plt.close('all')
    return page_counts


# - What are the most common headlines in VET (CVET respectively)?
# -> Cluster words and histogram after filtering
def cluster_headlines(structure_dicts: List[Dict],
                      element_type='paragraph',  # 'teil', 'abschnitt'
                      max_dist: int = 4,  # 4 am besten für paragraph
                      min_cluster_size: int = 2,
                      keep_clusters: int = None,
                      show_plot: bool = False,
                      plot_path: str = None) -> List[List[str]]:
    """
    Clusters (DBSCAN) the headlines based on a maximum Levenshtein distance between them
    :param structure_dicts:
    :param element_type: element type 'paragraph', 'teil', or 'abschnitt'
    :param max_dist: maximum Levenshtein distance between strings in a cluster
    :param min_cluster_size: number of headlines that need to be in a cluster to be kept
    :param keep_clusters:
    :param show_plot:
    :param plot_path:
    :return:
    """
    headlines = []
    for sad in structure_dicts:
        if element_type not in sad['text_structure']:
            continue
        text_elements = sad['text_structure'][element_type]
        for elem in text_elements:
            parsed_headline = " ".join(elem['headline'].lower().replace("&amp;", '').replace("<lb />", '').split("\n")[1:])  # Remove parts like "§ 1", "Abschnitt 1", "Erster Teil", ...
            headlines.append(parsed_headline)

    # Levenshtein distance is not supported by DBSCAN so a distance matrix needs to be precomputed
    distances = np.zeros((len(headlines), len(headlines)))
    for i in range(len(distances)):
        for j in range(len(distances[i])):
            distances[i][j] = distance(headlines[i], headlines[j])

    # DBSCAN with precomputed distance matrix
    epsilon = max_dist
    min_samples = min_cluster_size
    dbscan = DBSCAN(eps=epsilon, min_samples=min_samples, metric='precomputed')
    dbscan_clusters = dbscan.fit_predict(distances)

    clusters = [[] for _ in range(len(set(dbscan_clusters)) - 1)]  # -1 to ignore outliers
    for i in range(len(dbscan_clusters)):
        if dbscan_clusters[i] < 0:
            continue
        clusters[dbscan_clusters[i]].append(headlines[i])

    clusters.sort(key=lambda x: len(x))
    if keep_clusters is not None:
        clusters = clusters[(-1) * keep_clusters:]

    clusters = [cluster for cluster in clusters if len(cluster) >= min_cluster_size]

    cluster_labels = [(Counter(headline_list).most_common(1)[0][0], len(headline_list)) for headline_list in
                      clusters]

    if show_plot or plot_path is not None:
        # headline_occurrences is structured like:
        # {
        #   'cluster_label_1': 500
        #   'cluster_label_2': 480
        # }
        headline_occurrences = {}
        for label, occurrences in cluster_labels:
            if label not in headline_occurrences:
                headline_occurrences[label] = [occurrences]
            else:
                headline_occurrences[label].append(occurrences)

        fig, ax = plt.subplots(figsize=(12, 8))
        for label, occurrences in headline_occurrences.items():
            ax.bar([label] * len(occurrences), [(num_occurrences / len(structure_dicts)) * 100 for num_occurrences in occurrences], alpha=0.7)  # Get percentage of regulations with that headline

        ax.set_xlabel('Headline')
        ax.set_ylabel('Occurrences')
        ax.set_title('Headline occurrences')
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{x:.0f}%'))
        ax.set_xticks(range(len(headline_occurrences)))
        ax.set_xticklabels([label for label, _ in headline_occurrences.items()], rotation=90)
        ax.grid(axis='y')
        # plt.subplots_adjust(bottom=0.5, top=0.8)
        fig.tight_layout()

        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        plt.clf()
        plt.close('all')

    return clusters


# - Which parts become longer / shorter (Count lines or words in paragraph and map them to the headlines).
#     Again, cluster the headlines. Then, once this is done, lookup how many words are in each paragraph and so and
#     then, do a box plot with years on the x-axis and mean and std on the y-axis
def anaylze_paragraph_evolution_over_time(structure_dicts: List[Dict],
                                          element_type='paragraph',  # 'teil', 'abschnitt'
                                          max_dist: int = 4,
                                          min_cluster_size=1,
                                          keep_clusters: int = None,
                                          show_plot: bool = False,
                                          plot_path: str = None):
    headline_clusters = cluster_headlines(structure_dicts, keep_clusters=keep_clusters,
                                          element_type=element_type, max_dist=max_dist,
                                          min_cluster_size=min_cluster_size)
    cluster_labels = [(Counter(headline_list).most_common(1)[0][0], len(headline_list))
                      for headline_list in headline_clusters]
    # Build a dictionary with this structure:
    # {
    #   cluster_label_1: {
    #     year_1: [word_count_1, word_count_2, word_count_3, word_count_4]
    #   },
    #   cluster_label_2: {
    #     year_1: [word_count_1, word_count_2, word_count_3, word_count_4],
    #     year_2: [word_count_1, word_count_2, word_count_3, word_count_4]
    #   },
    # }

    result_dict = {}
    for structure_dict in structure_dicts:
        year = structure_dict['year']
        if year <= 1969 or year >= 2023:
            continue
        if element_type in structure_dict['text_structure'].keys():
            elements = structure_dict['text_structure'][element_type]
        else:
            continue
        for element in elements:
            for cluster_idx in range(len(headline_clusters)):
                sanitized_headline = " ".join(element['headline'].lower().replace("&amp;", '').replace("<lb />", '').split("\n")[1:])
                if sanitized_headline in headline_clusters[cluster_idx]:
                    if cluster_labels[cluster_idx][0] not in result_dict.keys():
                        result_dict[cluster_labels[cluster_idx][0]] = {year: []}
                    if year not in result_dict[cluster_labels[cluster_idx][0]]:
                        result_dict[cluster_labels[cluster_idx][0]][year] = []
                    result_dict[cluster_labels[cluster_idx][0]][year].append(element['words'])
                    break

    # "I play this game for the plot." The plot:
    if show_plot or plot_path is not None:
        # Get all years and sort them
        years = sorted(list(year for inner_dict in result_dict.values() for year in inner_dict.keys()))
        # Get the mean values of the lengths of the headline types
        means = {headline_label: [] for headline_label in result_dict.keys()}
        # Get the occurrences of each headline in each year
        relative_year_occurrences = {headline_label: [] for headline_label in result_dict.keys()}
        # Get the number of documents per year
        docs_per_year = {}
        for sd in structure_dicts:
            docs_per_year[sd['year']] = docs_per_year.get(sd['year'], 0) + 1
        for cluster_label, years_data in result_dict.items():
            for year in years:
                if year in years_data:
                    means[cluster_label].append(np.mean(years_data[year]))
                    relative_year_occurrences[cluster_label].append((len(years_data[year]) / docs_per_year.get(year, 1)) * 100)  # Normalize by documents per year
                else:
                    means[cluster_label].append(None)
                    relative_year_occurrences[cluster_label].append(None)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))  # , sharex='all'

        for cluster_label, values in means.items():
            ax1.plot(years, values, marker='o', label=cluster_label)
        ax1.set_ylabel(f'Mean {element_type} length')
        ax1.set_title(f'Mean {element_type} length in words over time')
        ax1.legend()
        ax1.grid(True)
        ax1.set_ylim(bottom=0)

        for cluster_label, values in relative_year_occurrences.items():
            ax2.plot(years, values, marker='o', label=cluster_label)
        ax2.set_xlabel('Year')
        ax2.set_ylabel(f'Occurrences of {element_type}')
        ax2.set_title(f'Occurrences of {element_type} over time')
        ax2.legend()
        ax2.grid(True)
        ax2.set_ylim(bottom=0)
        ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{x:.0f}%'))

        plt.tight_layout()

        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        fig.clf()
        plt.close('all')
    return result_dict


# ------------------------------------------------- WORD ANALYSIS -------------------------------------------------
# ------------------------------------------------- WORD ANALYSIS -------------------------------------------------
# ------------------------------------------------- WORD ANALYSIS -------------------------------------------------
# ------------------------------------------------- WORD ANALYSIS -------------------------------------------------


# Lemmatizer and Spell Checker
lemmatizer = spacy.load("de_core_news_sm")
german_dict = enchant.Dict("de_DE")  # The hunspell dict was downloaded previously and added in the dict directory!
hit_count = 0
miss_count = 0


# Spell Checking and Lemmatization Helpers
def lemmatize_word(word: str, lemmatizer: spacy.Language, max_iter: int = 4):
    lemmatized_word = lemmatizer(word)[0].lemma_
    current_iter = 0
    while lemmatized_word != word and current_iter < max_iter:
        word = lemmatized_word
        lemmatized_word = lemmatizer(word)[0].lemma_
        current_iter += 1
    return lemmatized_word


def spell_check_word(word: str, enchant_dict: enchant.Dict):
    if not enchant_dict.check(word):
        suggestions = enchant_dict.suggest(word)
        if suggestions:
            return suggestions[0].translate(str.maketrans('', '', string.punctuation))  # [char for char in suggestions[0] if char not in string.punctuation]
    return word


def process_word(word: str, enchant_dict: enchant.Dict, lemmatizer: spacy.Language, cache: Dict[str, str] = None):
    """
    Does spell checking and lemmatization for a string containing only one word
    :param word:
    :param enchant_dict:
    :param lemmatizer:
    :return:
    """
    global hit_count
    global miss_count
    lower_word = word.lower()
    if lower_word in cache.keys():
        result = cache[lower_word]
        hit_count += 1
        # print(f"HITS: {hit_count}")
    else:
        result = lemmatize_word(spell_check_word(word, enchant_dict), lemmatizer)
        cache[word] = result
        miss_count += 1
        # print(f"MISSES: {miss_count}")
    return result


def merge_dictionaries_with_counts(dict_list: List[Dict]):
    """
    Takes a list of dictionaries that map keys to a number and creates a dictionary that has the same keys and
    all number values of that particular key in the other dictionaries are added
    :param dict_list:
    :return:
    """
    # This is just a helper
    result_dict = {}
    for dict_item in dict_list:
        for k, v in dict_item.items():
            key_word = process_word(k, enchant_dict=german_dict, lemmatizer=lemmatizer, cache=word_cache) if len(k) > 0 else ''
            result_dict[key_word] = result_dict.get(key_word, 0) + v  # k.lower()
    return result_dict


# - How does the vocabulary change over time (word count -> Filter for substantives and so and filter:
#                                                         - Which are only in one regulation?
#                                                         - Are some of them no longer used over time?)?
#                                                     -> pandas um Ergebnisse zu speichern
def analyze_wording(word_dicts: List[Dict],
                    num_most_common_words: int = 10,
                    word_blacklist: List[str] = None,
                    show_plot: bool = False,
                    plot_path: str = None):
    """
    Gets the most common words of all regulations and plots its occurrences over time normalized by the number of words
    in each year
    :param word_dicts:
    :param num_most_common_words:
    :param word_blacklist:
    :param show_plot:
    :param plot_path:
    :return:
    """
    # Get all relevant word frequencies
    years = list(set([word_dict['year'] for word_dict in word_dicts
                      if 1969 <= word_dict['year'] <= 2023]))
    years.sort()

    if word_blacklist is None:
        word_blacklist = []

    # Remove stopwords
    print(word_blacklist)
    stop_words_german = set(stopwords.words('german'))
    for i in range(len(word_dicts)):
        word_dicts[i]['word_counts'] = {word: count for word, count in word_dicts[i]['word_counts'].items() if
                                        word not in stop_words_german and word.lower() not in string.punctuation
                                        and len(word.lower()) > 3 and word not in word_blacklist}

    # Get word frequencies per year
    word_freqs_per_year = {}
    for year in years:
        print(f"Processing {year}")
        word_freqs_per_year[year] = merge_dictionaries_with_counts([word_dict['word_counts'] for word_dict in word_dicts if int(word_dict['year']) == year])
        # word_freqs_per_year[year] = {word: count for word, count in word_freqs_per_year[year].items() if word not in word_blacklist}

    total_words_per_year = {}
    for year in word_freqs_per_year.keys():
        for _, v in word_freqs_per_year[year].items():
            total_words_per_year[year] = total_words_per_year.get(year, 0) + v

    # Get only the most relevant / often occurring words
    combined_word_counts = Counter()
    for year_data in word_freqs_per_year.values():
        combined_word_counts.update(year_data)
    most_common_words = combined_word_counts.most_common(num_most_common_words)

    if show_plot or plot_path is not None:
        words, counts = zip(*most_common_words)
        fig, ax = plt.subplots(figsize=(12, 8))
        for word in words:
            word_counts = [(word_freqs_per_year[year].get(word, 0) / max(total_words_per_year[year], 1)) * 100
                           for year in word_freqs_per_year]
            plt.plot(list(word_freqs_per_year.keys()), word_counts, label=word if word != 'anwend' else 'anwenden')  # As it was a known issue, for 'anwenden', this was fixed manually
        ax.set_xlabel('Year')
        ax.set_ylabel('Relative word occurrences')
        ax.set_title('Relative word count evolution over years')
        ax.legend()
        ax.grid(True)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{x:.2f}%'))
        if plot_path is not None:
            plt.savefig(plot_path)
        if show_plot:
            plt.show()
        plt.clf()
        plt.close('all')

    return total_words_per_year


def do_structure_analysis(structure_dicts: List[Dict], out_dir: str,
                          query: str = "SELECT year FROM public.regulation WHERE title LIKE 'Verordnung über die Berufsausbildung%'",
                          file_prefix: str = ''):
    out_regulation_years_path = os.path.join(out_dir, file_prefix + 'regulations_per_year.pdf')
    out_layout_type_path = os.path.join(out_dir, file_prefix + 'layout_types.pdf')
    out_text_element_count_path = os.path.join(out_dir, file_prefix + 'text_element_count.pdf')
    out_document_nesting_level_path = os.path.join(out_dir, file_prefix + 'document_nesting_level.pdf')
    out_pages_over_time_path = os.path.join(out_dir, file_prefix + 'pages_over_time.pdf')
    out_page_distribution_path = os.path.join(out_dir, file_prefix + 'page_distribution.pdf')
    out_most_relevant_headlines_path = os.path.join(out_dir, file_prefix + 'most_relevant_headlines.pdf')
    out_headlines_evolution_path = os.path.join(out_dir, file_prefix + 'headlines_evolution.pdf')
    print("Get years")
    print(compare_regulations_per_year(structure_dicts, query=query, show_plot=show_plots, plot_path=out_regulation_years_path))
    print("Count Layout Types")
    print(count_layout_types(structure_dicts, show_plot=show_plots, plot_path=out_layout_type_path))
    print("Count Text Elements")
    print(count_text_elements(structure_dicts, show_plot=show_plots, plot_path=out_text_element_count_path))
    print("Get Deepest Document Nesting")
    print(count_document_nesting_level(structure_dicts, show_plot=show_plots,
                                       plot_path=out_document_nesting_level_path))
    print("Count Pages Over Time")
    print(count_pages_over_time(structure_dicts, show_plot=show_plots, plot_path=out_pages_over_time_path))
    print("Get Page Distribution")
    print(count_page_distribution(structure_dicts, show_plot=show_plots, plot_path=out_page_distribution_path))
    print("Cluster Headlines")
    print(cluster_headlines(structure_dicts, keep_clusters=25, element_type='paragraph',
                            max_dist=4, min_cluster_size=10, show_plot=show_plots,
                            plot_path=out_most_relevant_headlines_path))
    print("Analyze Paragraph Evolution")
    print(anaylze_paragraph_evolution_over_time(structure_dicts, keep_clusters=10,
                                                element_type='paragraph', max_dist=4, min_cluster_size=10,
                                                show_plot=show_plots, plot_path=out_headlines_evolution_path))


def do_wording_analysis(wording_dicts: List[Dict], out_dir: str, file_prefix: str = '',
                        word_blacklist: List[str] = None):
    print("Do Wording Analysis")
    word_analysis_path = os.path.join(out_dir, file_prefix + 'wording_analysis.pdf')
    print(analyze_wording(wording_dicts, word_blacklist=word_blacklist,
                          show_plot=show_plots, plot_path=word_analysis_path))


show_plots = False
vet_word_blacklist = ['sowie', 'insbesondere']
cvet_word_blacklist = ['sowie', 'insbesondere']

# WICHTIG: Darauf achten, wo das word_cache dictionary gespeichert ist!

# # VET regulation processing
structure_analysis_directory = 'data_directory/evaluation/vet/structure'  # Alternativ: vet statt cvet
word_analysis_directory = 'data_directory/evaluation/vet/word_counts'  # Alternativ: vet statt cvet
evaluation_out_dir = 'data_directory/evaluation/vet/results'  # Alternativ: vet statt cvet
structure_json_files = [os.path.join(structure_analysis_directory, file_name)
                        for file_name in os.listdir(structure_analysis_directory)]
word_json_files = [os.path.join(word_analysis_directory, file_name)
                   for file_name in os.listdir(word_analysis_directory)]
structure_analysis_dicts = [json.load(open(file, 'r', encoding='utf-8')) for file in structure_json_files]
structure_analysis_dicts = [sad for sad in structure_analysis_dicts if 1969 <= sad['year'] <= 2023]
word_analysis_dicts = [json.load(open(file, 'r', encoding='utf-8')) for file in word_json_files]
word_analysis_dicts = [wad for wad in word_analysis_dicts if 1969 <= wad['year'] <= 2023]
word_cache = json.load(open("corrected_word_dictionaries/vet_lemmatized_dict.json", "r"))  # vet statt cvet für CVET regulations

compare_regulation_titles(structure_dicts=structure_analysis_dicts,
                          query="SELECT title FROM public.regulation WHERE title LIKE 'Verordnung über die Berufsausbildung%'")
do_structure_analysis(structure_dicts=structure_analysis_dicts,
                      query="SELECT year FROM public.regulation WHERE title LIKE 'Verordnung über die Berufsausbildung%'",
                      out_dir=evaluation_out_dir,
                      file_prefix='vet_')
do_wording_analysis(wording_dicts=word_analysis_dicts, word_blacklist=vet_word_blacklist,
                    out_dir=evaluation_out_dir, file_prefix='vet_')


# CVET regulation processing
# Loading and setting everything up
structure_analysis_directory = 'data_directory/evaluation/cvet/structure'  # Alternativ: vet statt cvet
word_analysis_directory = 'data_directory/evaluation/cvet/word_counts'  # Alternativ: vet statt cvet
evaluation_out_dir = 'data_directory/evaluation/cvet/results'  # Alternativ: vet statt cvet
structure_json_files = [os.path.join(structure_analysis_directory, file_name)
                        for file_name in os.listdir(structure_analysis_directory)]
word_json_files = [os.path.join(word_analysis_directory, file_name)
                   for file_name in os.listdir(word_analysis_directory)]
structure_analysis_dicts = [json.load(open(file, 'r', encoding='utf-8')) for file in structure_json_files]
structure_analysis_dicts = [sad for sad in structure_analysis_dicts if 1969 <= sad['year'] <= 2023]
word_analysis_dicts = [json.load(open(file, 'r', encoding='utf-8')) for file in word_json_files]
word_analysis_dicts = [wad for wad in word_analysis_dicts if 1969 <= wad['year'] <= 2023]
word_cache = json.load(open("corrected_word_dictionaries/cvet_lemmatized_dict.json", "r"))  # vet statt cvet für CVET regulations

compare_regulation_titles(structure_dicts=structure_analysis_dicts,
                          query="SELECT title FROM public.regulation WHERE title NOT LIKE 'Verordnung über die Berufsausbildung%'")
do_structure_analysis(structure_dicts=structure_analysis_dicts,
                      query="SELECT year FROM public.regulation WHERE title NOT LIKE 'Verordnung über die Berufsausbildung%'",
                      out_dir=evaluation_out_dir,
                      file_prefix='cvet_')
do_wording_analysis(wording_dicts=word_analysis_dicts, out_dir=evaluation_out_dir,
                    word_blacklist=cvet_word_blacklist,
                    file_prefix='cvet_')


# Some layout patterns seem pretty specific. Print their titles and have a look. -> Result: They indeed exist
# count = 0
# for sad in structure_analysis_dicts:
#     text_elems = sad['text_structure']
#     if 'teil' in text_elems.keys() and len(text_elems['teil']) == 2:
#         for teil in text_elems['teil']:
#             print(f"Teil: {teil['headline']}")
#         print(" ".join(sad['title'].split("\n")[1:]) + " - " + str(sad['year']))
#         count += 1
#     # if "zum anerkannten Fortbildungsabschluss" in sad['title']:  # 'deepest_text_nesting'
#     #     print(" ".join(sad['title'].split("\n")) + " - " + str(sad['page_count']) + " - " + str(sad['year']))
#     #     count += 1
# print(count)

# pages = [sad['page_count'] for sad in structure_analysis_dicts if sad['page_count'] <= 5]
# print(len(pages) / len(structure_analysis_dicts))
