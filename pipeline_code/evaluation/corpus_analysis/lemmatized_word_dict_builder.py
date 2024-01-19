import string
import enchant
import spacy
import json
import os
from nltk.corpus import stopwords
from concurrent.futures import ThreadPoolExecutor


def lemmatize_word(word: str, lemmatizer: spacy.Language, max_iter: int = 4):
    lemmatized_word = lemmatizer(word)[0].lemma_
    iter_count = 0
    while lemmatized_word != word and iter_count < max_iter:
        word = lemmatized_word
        lemmatized_word = lemmatizer(word)[0].lemma_
        iter_count += 1
    return lemmatized_word


def spell_check_word(word: str, enchant_dict: enchant.Dict):
    if not enchant_dict.check(word):
        suggestions = enchant_dict.suggest(word)
        if suggestions:
            return suggestions[0].translate(str.maketrans('', '', string.punctuation))  # [char for char in suggestions[0] if char not in string.punctuation]
    return word


def process_word(word: str, enchant_dict: enchant.Dict, lemmatizer: spacy.Language):
    return lemmatize_word(spell_check_word(word, enchant_dict), lemmatizer)


lemmatizer = spacy.load("de_core_news_sm")
german_dict = enchant.Dict("de_DE")  # The hunspell dict was downloaded previously and added in the dict directory of enchant!

word_analysis_directory = 'data_directory/evaluation/cvet/word_counts'  # Alternativ: vet statt cvet
word_json_files = [os.path.join(word_analysis_directory, file_name)
                   for file_name in os.listdir(word_analysis_directory)]
word_analysis_dicts = [json.load(open(file, 'r', encoding='utf-8')) for file in word_json_files]
word_analysis_dicts = [wad for wad in word_analysis_dicts if 1969 <= wad['year'] <= 2023]

all_words = set()
for wad in word_analysis_dicts:
    for k in wad['word_counts'].keys():
        all_words.add(k.lower())

all_words_copy = all_words.copy()
stop_words_german = set(stopwords.words('german'))
for w in all_words_copy:
    if w in string.punctuation or len(w) < 4 or w in stop_words_german:
        all_words.remove(w)

result_dict = {}


print(f"Number of words: {len(all_words)}")


# Function to process each segment of the set
def process_segment(segment):
    count = 0
    for word in segment:
        result_dict[word] = process_word(word, enchant_dict=german_dict, lemmatizer=lemmatizer)
        count += 1
        if count % 500 == 0:
            print(f"Current dict size: {len(result_dict)} - {(len(result_dict) / len(all_words))*100}%")


# Function to segment the word set
def segment_and_process(data_set, num_threads):
    data_list = list(data_set)
    segment_size = len(data_list) // num_threads
    segmented_data = [data_list[i:i + segment_size] for i in range(0, len(data_list), segment_size)]
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(process_segment, segmented_data))
    return results


# Do the processing in multicore mode
segment_and_process(all_words, 8)
with open("corrected_word_dictionaries/cvet_lemmatized_dict.json", "w") as outfile:
    json.dump(result_dict, outfile)
