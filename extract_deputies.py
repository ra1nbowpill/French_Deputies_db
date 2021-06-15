# coding: utf8

import re
import os
import sys
import csv
import unicodedata
import urllib.request

from tqdm import tqdm
from bs4 import BeautifulSoup


def fix_auto_closing(doc):
    """
    Auto closes meta and link tags in html document
    :param doc: html document
    :type doc: str
    :return: html document
    :rtype: str
    """
    document = ""
    for line in doc:
        line = line.decode("utf-8")
        if "<meta" in line:
            line = re.sub("<(meta.*?)>", "<\\1/>", line)
        if "<link" in line:
            line = re.sub("<(link.*?)>", "<\\1/>", line)
        document += line
    return document


def get_url(url):
    """
    Retrieves a document from the internet and make a BeautifulSoup out of it
    :param url: url for the document to be processed
    :return: a beautiful soup of the document
    :rtype: BeautifulSoup
    """
    page = urllib.request.urlopen(url)
    doc = fix_auto_closing(page)
    return BeautifulSoup(doc, 'html.parser')


def get_urls(page_deputies_table):
    """
    Url in the rows of the following webpage:
      http://www2.assemblee-nationale.fr/deputes/liste/tableau
    :param page_deputies_table:
    :type page_deputies_table: BeautifulSoup
    :return: urls to deputies info page
    :rtype: list of str
    """
    rows = page_deputies_table.table.tbody.find_all("tr")
    return [tr.a["href"] for tr in rows]


def norm_str(str_):
    """
    Applies normalisation to given string
    :param str_: a string
    :return: normalized string
    """
    return unicodedata.normalize("NFKD", str_).strip()


def extract_info(deputy_page):
    """
    Extract information of a deputy
    It's mostly a big hack, this is non reusable code
    :param deputy_page: content of deputy webpage
    :type deputy_page: BeautifulSoup
    :return: dictionary of information
    :rtype: dict
    """
    res = dict()

    # extract info from header
    header = deputy_page.find_all(class_="titre-bandeau-bleu")[0]
    header = [w for w in header.text.split('\n') if w != ""][:3]
    res["name"] = header[0]
    res["circonscription"] = header[1]
    res["state"] = header[2]

    # extract info from illustration
    illustration = deputy_page.find(id="deputes-illustration")
    res["group"] = illustration.text
    res["group_url"] = illustration.find_all("span")[-1].a["href"]

    # extract info from attributes
    attributes_tag = illustration.next_sibling.next_sibling
    for dt in attributes_tag.find_all("dt"):
        pp = dt.next_sibling.next_sibling.ul
        dt_val = dt.text.lower()
        if "commission" in dt_val:
            res["commission"] = pp.text.strip()
            res["commission_url"] = base + pp.li.a["href"]

        elif "biographie" in dt_val:
            bio = pp.find_all("li")[0].text.strip()
            bio = re.sub("\t|\n", " ", bio)
            bio = re.sub(" +", " ", bio)
            res["date_of_birth"] = re.sub("Née? le (.*) à .*", "\\1", bio)
            res["place_of_birth"] = re.sub("Née? le .* à (.*)", "\\1", bio)

        elif "suppl" in dt_val:
            res["substitute"] = pp.text.strip()

        elif "contact" in dt_val:
            if len(pp.find_all("li")) != 0:
                res["email"] = re.sub("mailto:", "", pp.li.a["href"])

        elif "financement" in dt_val:
            res["fundings"] = pp.text.strip()

        elif "claration" in dt_val:
            if len(pp.find_all("li")) != 0:
                res["decl_interet_activite_url"] = pp.li.a["href"]

    # extract info from contact section
    contact_section = deputy_page.find(id="deputes-contact").section.dl
    tel = []
    for elt in contact_section.find_all(class_="tel"):
        if elt.span.text != "":
            tel += [elt.span.text]
    res["phone"] = tel

    mail = [res["email"]] if "email" in res else []
    for elt in contact_section.find_all(class_="email"):
        mail += [re.sub("mailto:", "", elt["href"])]
    res["email"] = set(mail)

    adr = []
    for elt in contact_section.find_all(class_="adr"):
        address = re.sub(" +", " ", re.sub("\n", " ", elt.text)).strip()
        if "circonscription" in address:
            adr += [re.sub("En circonscription ", "", address)]
    res["address"] = adr

    for k, v in res.items():
        if isinstance(res[k], list):
            res[k] = [norm_str(s) for s in res[k]]
        elif isinstance(res[k], str):
            res[k] = norm_str(res[k])

    return res


def info_to_str_list(info):
    to_write = []
    # custom to_string
    for k in res_key:
        if k not in info:
            to_write += [""]
            continue

        if isinstance(info[k], set):
            info[k] = list(info[k])

        if isinstance(info[k], list):
            if len(info[k]) == 0:
                to_write += [""]
            elif len(info[k]) == 1:
                to_write += ["'" + str(info[k][0]) + "'"]
            else:
                to_write += [str(info[k])[1:-1]]
        else:
            to_write += [info[k]]
    return to_write


# keys of dictionary returned by extract_info
res_key = [
    'name', 'email', 'phone',
    'date_of_birth', 'place_of_birth',
    'circonscription', 'state',
    'group', 'group_url',
    'commission', 'commission_url',
    'substitute', 'fundings',
    'decl_interet_activite_url', 'address',
    'info_url'
]


base = 'http://www2.assemblee-nationale.fr'
liste = '/deputes/liste/tableau'

if __name__ == '__main__':

    # where to write the output
    output_file = 'deputies.csv'

    already_written = []

    write_header = True
    if os.path.exists(output_file):
        write_header = False
        with open(output_file, 'r') as csv_file:
            file_reader = csv.DictReader(
                csv_file, delimiter=';', quotechar='"')
            for row in file_reader:
                already_written += [row['info_url']]

    with open(output_file, 'a', newline='') as csv_file:
        file_writer = csv.writer(
            csv_file, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        if write_header:
            file_writer.writerow([k for k in res_key])

        sys.stderr.write("🌳  Retrieving deputies list ... ")
        # get the web page containing the list of deputies
        document = get_url(base + liste)
        # extracting urls to deputies info page
        urls = get_urls(document)
        sys.stderr.write("Done\n")

        urls = set(urls) - set(already_written)

        if len(urls) == 0:
            sys.stderr.write("🌍  Everything was already extracted\n")
            csv_file.close()
            exit()

        sys.stderr.write("📝  Retrieving information ...\n")

        for url in tqdm(urls):
            deputy_page = get_url(base + url)
            info = extract_info(deputy_page)
            info["info_url"] = url
            file_writer.writerow(info_to_str_list(info))

    sys.stderr.write("🌍  It's all done\n")
