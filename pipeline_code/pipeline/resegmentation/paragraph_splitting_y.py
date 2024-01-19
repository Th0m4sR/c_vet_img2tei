from lxml import etree
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from ..constants import NAMESPACES
from pipeline.hocr_tools.hocr_helpers import get_element_bbox, get_surrounding_bbox
from ..hocr_tools.hocr_properties import carea_contins_only_empty_words

"""
This is the main part responsible for splitting the paragraphs
"""


def split_ocr_careas_horizontally(hocr_tree: etree.ElementTree, max_line_space: int = None):
    """
    Takes an hOCR tree and splits all ocr_careas into multiple new ones depending on the distances between lines
    with ocr_careas
    :param hocr_tree: parsed hOCR tree that will be split in place
    :param max_line_space:  maximum space before areas are split
    :return:
    """
    if max_line_space is None:
        max_line_dist = compute_maximum_linespace(hocr_tree)
        if max_line_dist < 0:
            return
    else:
        max_line_dist = max_line_space
    ocr_pages = hocr_tree.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES)
    for page in ocr_pages:
        careas = page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
        for carea in careas:
            carea_parent = carea.getparent()
            pars = carea.xpath(".//x:p[@class='ocr_par']", namespaces=NAMESPACES)
            changed = False
            for par in pars:
                lines = par.xpath("./x:span[@class='ocr_line' or @class='ocr_textfloat']", namespaces=NAMESPACES)
                if lines:
                    changed = True
                    new_carea = etree.Element("{http://www.w3.org/1999/xhtml}div")
                    new_carea.set("class", "ocr_carea")
                    new_p = etree.Element("{http://www.w3.org/1999/xhtml}p")
                    new_p.set("class", "ocr_par")
                    # The first new paragraph starts with the first line
                    new_p.append(lines[0])
                    for i in range(1, len(lines)):
                        _, _, _, y2_prev = get_element_bbox(lines[i-1])
                        _, y1, _, _ = get_element_bbox(lines[i])
                        # Compute the line distance
                        if abs(y1 - y2_prev) <= max_line_dist:
                            # If the lines are close enough to each other, combine them into the same paragraph
                            new_p.append(lines[i])
                        else:
                            # Otherwise, create the next paragraph
                            # Append the new par to the new carea
                            new_carea.append(new_p)
                            # Set the title attribute
                            x1, y1, x2, y2 = get_surrounding_bbox(new_p.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat']", namespaces=NAMESPACES))
                            new_p.set("title", f"bbox {x1} {y1} {x2} {y2}")
                            new_carea.set("title", f"bbox {x1} {y1} {x2} {y2}")

                            # Add elements in front of the current area to keep the ordering
                            carea.addprevious(new_carea)

                            # Create the next new carea and paragraph
                            new_carea = etree.Element("{http://www.w3.org/1999/xhtml}div")
                            new_carea.set("class", "ocr_carea")
                            new_p = etree.Element("{http://www.w3.org/1999/xhtml}p")
                            new_p.set("class", "ocr_par")

                            new_p.append(lines[i])
                    # After the for loop, the paragraph still needs to be added to the tree
                    new_carea.append(new_p)
                    x1, y1, x2, y2 = get_surrounding_bbox(new_p.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat']", namespaces=NAMESPACES))
                    new_p.set("title", f"bbox {x1} {y1} {x2} {y2}")
                    new_carea.set("title", f"bbox {x1} {y1} {x2} {y2}")
                    # After that, the original par needs to be removed
                    par_parent = par.getparent()
                    par_parent.remove(par)
                    carea.addprevious(new_carea)
            if changed:
                carea_parent.remove(carea)  # If an ocr_carea was split, the parent is removed
    # This will re-combine areas that were split but should be in one area
    remerge_oversplit_careas(hocr_tree, max_line_dist=max_line_dist)


def combine_careas(carea_1, carea_2):
    """
    Appends all lines from carea_2 to carea_1, redefines the bounding box of carea_1, and detaches carea_2 from its
    parent
    :param carea_1:
    :param carea_2:
    :return:
    """
    # Move lines from carea_2 to carea_1
    pars = carea_1.xpath(".//x:p[@class='ocr_par']", namespaces=NAMESPACES)
    if len(pars) > 0:
        elem_to_append_on = pars[0]
    else:
        elem_to_append_on = carea_1
    for line in carea_2.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']", namespaces=NAMESPACES):
        elem_to_append_on.append(line)
    # Build the new bbox
    new_lines = carea_1.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']", namespaces=NAMESPACES)
    try:
        x1, y1, x2, y2 = get_surrounding_bbox(new_lines)
        carea_1.set("title", f"bbox {x1} {y1} {x2} {y2}")
    except Exception as e:
        # If get_surrounding_bbox is not working, do not merge
        return
    # Remove carea_2 from its parent.
    parent = carea_2.getparent()
    if parent is not None:
        parent.remove(carea_2)


def remerge_oversplit_careas(hocr_tree: etree.ElementTree, max_line_dist):
    """
    Merges ocr_careas that should not have been split but was by the OCR engine.
    If an ocr_carea in the hocr_tree ends with an "-", it will be merged with the upcoming carea
    :param hocr_tree: hOCR tree that will be remerged in place
    :param max_line_dist: The maximum line distance where careas will be combined if they are that close to each other
    :return:
    """
    # Verursacht z.T. Fehler: bbbox über gesamte Seite...
    #  1. Sicherstellen, dass die careas untereinander und nicht übereinander sind (Das später abfangen im
    #  fertigen Dokument
    #  2. Die line split distance nutzen und dann alles, was näher beisammen ist, mergen
    careas = hocr_tree.xpath("///x:body/x:div[@class='ocr_page']//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    carea_idx = 0
    while carea_idx < len(careas) - 1:
        upper_carea = get_element_bbox(careas[carea_idx])
        lower_carea = get_element_bbox(careas[carea_idx+1])
        if (np.abs(lower_carea[1] - upper_carea[3]) <= max_line_dist) and \
                not carea_contins_only_empty_words(careas[carea_idx+1]) and \
                not carea_contins_only_empty_words(careas[carea_idx]):
            combine_careas(careas[carea_idx], careas[carea_idx+1])
            del careas[carea_idx+1]
        else:
            carea_idx += 1


"""
This part of the code is used to compute the line distance and the maximum line distance that a paragraph may have
"""


def filter_iqr(data, lower_percentile: int = 15, upper_percentile: int = 85):
    """
    Performs IQR filtering on the input dataset
    :param data: scalar data to be filtered
    :param lower_percentile:
    :param upper_percentile:
    :return: The filtered input data set
    """
    # Calculate Q1 (25th percentile) and Q3 (75th percentile)
    q1 = np.percentile(data, lower_percentile)
    q3 = np.percentile(data, upper_percentile)
    # Calculate the Interquartile Range (iqr)
    iqr = q3 - q1
    # Calculate lower and upper bounds for outliers
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    # Filter the data within the bounds
    filtered_data = np.array([x for x in data if lower_bound <= x <= upper_bound]).reshape(-1, 1)
    return filtered_data


def get_line_distances_per_ocr_carea(hocr_tree: etree.ElementTree) -> np.array:
    """
    Computes the line distances for lines in each ocr_carea and not across different_ocr_careas
    :param hocr_tree:
    :return:
    """
    ocr_careas = hocr_tree.xpath("///x:body/x:div[@class='ocr_page']//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    line_distances = []
    for ocr_carea in ocr_careas:
        lines = ocr_carea.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat']", namespaces=NAMESPACES)
        for i in range(1, len(lines)):
            _, _, _, prev_y2 = get_element_bbox(lines[i-1])
            _, y1, _, _ = get_element_bbox(lines[i])
            if y1 > prev_y2:
                line_distances.append(y1 - prev_y2)
    return np.array(line_distances).reshape(-1, 1)


def compute_maximum_linespace(hocr_tree: etree.ElementTree, plot_clusters: bool = False) -> float:
    """
    Takes line distances to find the maximum distance two lines can have within the same paragraph.
    The procedure uses k-Means with k=2 and then takes the highest point of the lower cluster as maximum line width.
    This was chosen due to the observation that there are often two centers of mass
    :param hocr_tree: Parsed hOCR ElementTree which the maximum line distance of a cluster is computed
    :param plot_clusters: boolean that tests if the labels should be plotted
    :return: maximum distance two lines can have within the same paragraph
    """
    # Setup line distances and filter outliers
    line_distances = filter_iqr(get_line_distances_per_ocr_carea(hocr_tree))
    if len(line_distances) < 2:
        return -1
    # Specify the number of labels
    num_clusters = 2  # Two labels because the observation was that there are 2 centers of mass
    kmeans = KMeans(n_clusters=num_clusters, n_init='auto')
    cluster_labels = kmeans.fit_predict(line_distances)
    # Initialize a list to store filtered data for each cluster
    filtered_data_per_cluster = []
    # Filter smaller outliers from the labels to improve results
    for i in range(num_clusters):
        # Get data points belonging to the current cluster
        cluster_data = line_distances[cluster_labels == i]
        # Calculate the first and third quartiles
        #  Filtering finer to not remove too much data
        q1 = np.percentile(cluster_data, 0)
        q3 = np.percentile(cluster_data, 100)
        # Calculate the IQR
        iqr = q3 - q1
        # Define the lower and upper bounds to identify outliers
        lower_bound = q1 - 1.5 * iqr  # 1.5 is often used
        upper_bound = q3 + 1.5 * iqr  # 2 instead of 1.5 to allow more points as actual data
        # Filter out outliers within the current cluster
        filtered_cluster_data = cluster_data[(cluster_data >= lower_bound) & (cluster_data <= upper_bound)]
        filtered_data_per_cluster.append(filtered_cluster_data)

    cluster_min_vals = [min(x) for x in filtered_data_per_cluster]

    lower_cluster_index = np.argmin(cluster_min_vals)  # Needs to be computed dynamically
    # upper_cluster_index = np.argmax(cluster_min_vals)

    max_lower_cluster_value = np.max(filtered_data_per_cluster[lower_cluster_index])
    # min_upper_cluster_value = np.min(filtered_data_per_cluster[upper_cluster_index])

    max_line_dist = max_lower_cluster_value  # max_lower_cluster_value + ((min_upper_cluster_value - max_lower_cluster_value) / 2)

    if plot_clusters:
        # Creating a figure with subplots
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(10, 10))

        # Plotting Scatter plot with horizontal lines
        ax1.scatter(x=[i for i in range(len(line_distances))], y=line_distances, color='blue', label='Line Distance')
        ax1.axhline(y=np.mean(line_distances), color='green', linestyle='--', label='Mean')
        ax1.axhline(y=np.mean(line_distances) + np.std(line_distances), color='black', linestyle='--',
                    label='Standard Deviation')
        ax1.axhline(y=np.mean(line_distances) - np.std(line_distances), color='black', linestyle='--',
                    label='Standard Deviation')
        ax1.axhline(y=max_line_dist, color='red', linestyle='--', label='Threshold')
        ax1.set_xlabel('Box Index')
        ax1.set_ylabel('Line distance')
        ax1.set_title('Distances between lines')
        ax1.legend()
        ax1.grid()

        # Plotting the histogram on the second subplot
        ax2.hist(line_distances, bins=30, alpha=0.5, color='blue')
        ax2.set_xlabel('Value')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Histogram of Line Distances')
        ax2.grid()
        ax2.axvline(x=max_line_dist, color='red', linestyle='--', label='Threshold')

        # Adjust layout and display the figure
        plt.tight_layout()
        plt.show()
    return max_line_dist
