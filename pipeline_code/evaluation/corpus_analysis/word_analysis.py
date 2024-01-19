from lxml import etree
from pipeline.constants import TEI_NAMESPACE
import tei_tools
from typing import Dict
import re


NAMESPACES = {'x': TEI_NAMESPACE}


def count_p_words(regulation_tree: etree.ElementTree) -> Dict[str, int]:
    pars = regulation_tree.xpath(".//x:p", namespaces=NAMESPACES)
    word_counts = {}
    for par in pars:
        lines = tei_tools.build_element_lines(par)
        words = " ".join(lines).split(" ")
        word_idx = 0
        while word_idx < len(words):
            if words[word_idx].endswith("-") and word_idx < len(words) - 1:
                words[word_idx] = words[word_idx][:-1] + words[word_idx+1]
            word_idx += 1
        for word_idx in range(len(words)):
            word = re.sub(r'[^\w\d\s]', '', words[word_idx])
            word_counts[word] = word_counts.get(word, 0) + 1
    return word_counts


def count_p_total_words(regulation_tree: etree.ElementTree) -> int:
    pars = regulation_tree.xpath(".//x:p", namespaces=NAMESPACES)
    word_count = 0
    for par in pars:
        words = " ".join(tei_tools.build_element_lines(par)).split(" ")
        word_count += len(words)
    return word_count


def count_p_lines(regulation_tree: etree.ElementTree) -> int:
    pars = regulation_tree.xpath(".//x:p", namespaces=NAMESPACES)
    line_count = 0
    for par in pars:
        line_count += count_text_element_lines(par)
    return line_count


def count_text_element_lines(elem: etree.ElementTree) -> int:
    line_breaks = elem.xpath(".//x:lb", namespaces=NAMESPACES)
    return len(line_breaks) + 1
