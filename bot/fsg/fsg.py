# !/usr/bin/python3
# coding: utf-8

import csv
import os
import time

from bs4 import BeautifulSoup
from hal.files.models import Document, FileSystem
from hal.internet.parser import html_stripper
from hal.internet.selenium import SeleniumForm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PATH_TO_THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
PATH_TO_CHROMEDRIVER = os.path.join(PATH_TO_THIS_DIRECTORY, "chromedriver")  # to proper work with selenium
BROWSER_WAIT_TIMEOUT_SECONDS = 2
DNF_VALUE = ""


def close_alert_in_time(driver, max_time):
    """
    :param driver: selenium web driver
        web driver to use
    :param max_time: int
        Max seconds to wait for alert
    :return: void
        Close all alerts popping up in max_time seconds interval
    """

    max_time_wait = time.time() + max_time
    is_alert_dismissed = False
    while time.time() < max_time_wait and not is_alert_dismissed:
        if is_alert_dismissed:  # can exit loop
            break
        try:
            driver.switch_to.alert.accept()  # discard any pop-up
            is_alert_dismissed = True
        except Exception:
            time.sleep(0.2)


def navigate_to_prev_page(driver):
    """
    :param driver: selenium web driver
        web driver to use
    :return: void
        force web driver to get to previous page
    """

    driver.execute_script("window.history.go(-1)")  # go back
    driver.refresh()  # refresh page


class ESFFormSection(object):
    """ Chapter of an ESF form """

    def __init__(self, name, table):
        """
        :param name: string
            Name of chapter
        :param table: soup
            Beautifusoup wrapper for raw html table
        """

        object.__init__(self)

        self.name = name
        self.table = table

    def get_label_input_list(self):
        """
        :return: [] of {}
            List of dictionaries with labels and respective 'name' attribute
        """

        label_input_list = []
        for row in self.table.find_all("tr")[1:]:  # cycle through all rows except first one (there are the labels)
            label_input = self.get_table_row_input(row)
            label_input_list.append(label_input)
        return label_input_list

    @staticmethod
    def get_table_row_input(row):
        """
        :return: dict
            Parses table row and returns a dictionary like <key: name of value to upload, value: name attribute of item>
        """

        try:
            row_label = row.find_all("th")[0].text  # labels of table are here: get only first label
        except:
            row_label = DNF_VALUE

        try:
            row_input = row.find_all("th")[0].find_all("label")[0]["for"]
        except Exception:
            row_input = DNF_VALUE

        return {
            "label": row_label,
            "input": row_input
        }


class ESFForm(object):
    """ ESF form in FSG webpage """

    def __init__(self, name, status, show_function):
        """
        :param name: string
            Name of form
        :param status: string
            Status of form
        :param show_function: string
            Javascript function to show form
        """

        object.__init__(self)

        self.name = name
        self.status = status
        self.show_function = show_function


class ESFFormBot(object):
    """ ESF form bot to upload this form only to FSG webpage """

    def __init__(self, browser, form):
        """
        :param browser: webdriver
            Browser to use.
        :param form: ESFForm
            Form to upload
        """

        object.__init__(self)

        self.browser = browser
        self.form = form

    def upload_data(self, data_file_to_upload):
        """
        :param data_file_to_upload: str
            Path to .csv file containing subsections data to upload
        :return: void
            Uploads data of all subsections in this form
        """

        label_value_list = self.get_label_value_list_from_data(
            data_file_to_upload)  # get {label -> value} list from data

        self.browser.execute_script(self.form.show_function)  # go to page of esf form sections
        WebDriverWait(self.browser, BROWSER_WAIT_TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.NAME, "submit"))
        )  # wait until fully loaded
        soup = BeautifulSoup(self.browser.page_source, "lxml")

        sections_title = soup.find_all("h3")[1:]  # discard first title
        sections_data = soup.find_all("table", {"class": "overview"})
        for i in range(len(sections_title)):  # cycle through all sections
            section = ESFFormSection(
                html_stripper(sections_title[i].text),  # find title
                sections_data[i]  # find table
            )  # create section from raw data
            self.upload_subsection_data(section, label_value_list)

        self.browser.execute_script(
            "document.getElementsByName(\"submit\")[1].click()")  # click button # click 'save' button

    def upload_subsection_data(self, subsection, label_value_list):
        label_input_list = subsection.get_label_input_list()  # get {label -> input} list
        input_value_list = []  # get {input -> value} list
        for li in label_input_list:
            i = li["input"]
            l = li["label"]

            v = DNF_VALUE  # find dict with that label
            for d in label_value_list:
                if str(d["label"])[:32].lower() == str(l)[:32].lower():
                    v = d["value"]  # get value of label

            input_value_list.append(
                {
                    "input": i,
                    "value": v
                }  # match input -> value
            )

        print("\t\tUploading data about sub-section", subsection.name)
        for iv in input_value_list:
            input_name = iv["input"]
            value_content = iv["value"]

            if input_name != DNF_VALUE:
                try:
                    self.browser.execute_script(
                        "document.getElementById(\"" + input_name + "\").value = \"" + str(value_content) + "\"")
                except Exception:
                    print("!!! Cannot set value of input", input_name)

    @staticmethod
    def get_label_value_list_from_data(data_file):
        """
        :param data_file: str
            Path to .csv file containing subsections data to upload
        :return: [] of {}
            Parses data file to get the list of dictionaries like <key: label in form, value: value to upload>
        """

        label_value_list = []
        with open(data_file, "r") as c:
            reader = csv.reader(c, delimiter=",", quotechar="\"")
            for row in reader:
                try:  # retrieve label and value
                    label = row[0]
                    value = row[1]
                except:
                    label = DNF_VALUE
                    value = DNF_VALUE

                label_value_list.append(
                    {
                        "label": label,
                        "value": value
                    }
                )

        return label_value_list


class ESFFormScraperBot(object):
    """ Scrape ESF from FSG webpage """

    ESF_URL = "https://www.formulastudent.de/esf"

    def __init__(self, browser):
        """
        :param browser: webdriver
            Browser to use.
        """

        object.__init__(self)

        self.browser = browser

    def get_esf_form_sections(self):
        """
        :return: list of ESFForm
            ESFForm parsed from given raw html table
        """

        self.browser.get(ESFFormScraperBot.ESF_URL)  # go to list of ESFs

        soup = BeautifulSoup(self.browser.page_source, "html.parser")  # parse source page
        table = soup.find_all("table", {"class": "overview"})[0]
        esf_list = []
        rows = table.find_all("tr")[1:]  # find all rows
        for row in rows:
            name = row.find_all("th")[0].text
            status = row.find_all("td")[0].text
            show_function = row.find_all("td")[1].find_all("input")[0]["onclick"]
            esf_list.append(
                ESFForm(
                    html_stripper(name),
                    html_stripper(status),
                    html_stripper(show_function)
                )
            )  # append just found element
        return esf_list


class FSGermanyEsfUploadBot(object):
    """ Bot to upload esf to FSG webpage """

    def __init__(self, browser, data_folder):
        """
        :param browser: web-driver
            Browser to use.
        :param data_folder: str
            Path to folder containing esf data
        """

        object.__init__(self)

        self.browser = browser
        self.data_folder = data_folder

    def upload_data(self):
        """
        :return: void
            Uploads text of all esf section to esf webpage
        """

        bot = ESFFormScraperBot(self.browser)  # build bot to scrape esf main page
        esf_form_sections = bot.get_esf_form_sections()  # find all esf form sections
        for section in esf_form_sections:
            print("Uploading sub-form", section.name)
            try:
                self.browser.get(ESFFormScraperBot.ESF_URL)
                self._upload_data_of_form(section)
            except Exception:
                print("Cannot upload sub-form", section.name)

    def _upload_data_of_form(self, esf_form_section):
        """
        :param esf_form_section: ESFForm
            Esf form section
        :return: void
            Uploads data of selected section
        """

        data_file = self._find_data_file_of_section(esf_form_section)  # path to file containing data about section
        print("\tUsing data file", data_file)

        bot = ESFFormBot(self.browser, esf_form_section)  # build bot to upload single form section
        bot.upload_data(data_file)

    def _find_data_file_of_section(self, esf_form_section):
        """
        :param esf_form_section: str
            Name of form section to find relative data file of
        :return: str
            Path to file containing data about section
        """

        data_files_list = FileSystem.ls(self.data_folder, False, False)
        for f in data_files_list:
            if os.path.isfile(f):
                doc = Document(f)
                if esf_form_section.name in doc.name:  # match section to file name
                    return f
        return ""


class FSGermanyLoginBot(object):
    """ Bot to perform login in FSG webpage """

    LOGIN_URL = "https://www.formulastudent.de/l/?redirect_url=%2F"

    def __init__(self, browser, user, password):
        """
        :param browser: webdriver
            Browser to use.
        :param user: string
            Username to perform login
        :param password: string
            User password to perform login
        """

        object.__init__(self)

        self.browser = browser
        self.user = user
        self.password = password

    def login(self):
        """
        :return: void
            Login in FSG website.
        """

        self.browser.get(FSGermanyLoginBot.LOGIN_URL)  # open login url
        SeleniumForm.fill_login_form(
            self.browser,
            self.user, "user",
            self.password, "pass"
        )  # fill login form
        SeleniumForm.submit_form(self.browser, "submit")  # press login button
        WebDriverWait(self.browser, BROWSER_WAIT_TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "c2106"))
        )  # wait until fully loaded


class FSGermanyBot(object):
    """ Bot to navigate through Formula Student Germany webpage"""

    def __init__(self):
        object.__init__(self)

        self.browser = webdriver.Chrome(PATH_TO_CHROMEDRIVER)

    def login(self, user, password):
        """
        :param user: string
            Username to perform login
        :param password: string
            User password to perform login
        :return: void
            Login in FSG website.
        """

        bot = FSGermanyLoginBot(self.browser, user, password)  # create bot for login
        bot.login()  # perform login

    def upload_esf(self, data_folder):
        """
        :param data_folder: str
            Path to folder containing esf data
        :return: void
            Uploads text of all esf section to esf webpage
        """

        bot = FSGermanyEsfUploadBot(self.browser, data_folder)
        bot.upload_data()

    def exit(self):
        self.browser.close()
