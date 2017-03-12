# !/usr/bin/python
# coding: utf-8

# Copyright 2017 Stefano Fogarollo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import time

from bs4 import BeautifulSoup
from hal.internet.parser import html_stripper
from hal.internet.selenium import SeleniumForm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PATH_TO_THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
PATH_TO_CHROMEDRIVER = os.path.join(PATH_TO_THIS_DIRECTORY, "chromedriver")  # to proper work with selenium
OUTPUT_FOLDER = os.path.join(PATH_TO_THIS_DIRECTORY, "esf", str(int(time.time())))
BROWSER_WAIT_TIMEOUT_SECONDS = 2


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
        except:
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
        self.data = None  # 2D matrix that contain all values from html table
        self.upload_items = []  # TODO parse list of dict <key: name of value to upload, value: id of item>
        self.show_functions = []  # javascript show methods to show extra data

    def parse(self, browser):
        """
        :param browser: webdriver
            Browser to use.
        :return: void
            Parse raw html table and save results
        """

        def get_show_functions():
            """
            :return: list
                Get javascript methods to open esf sections and return table data
            """

            data = []  # output 2D matrix that contain all values from html table
            for row in self.table.find_all("tr"):  # cycle through all rows
                row_items = []  # array of elements of this row
                for column_label in row.find_all("th"):
                    row_items.append(html_stripper(column_label.text))

                for column in row.find_all("td"):  # cycle through all columns
                    try:
                        show_function = column.a["onclick"].split(";")[0]  # remove return statement
                        self.show_functions.append(show_function)
                    except:
                        pass
                    row_items.append(html_stripper(column.text))  # get new table entry
                data.append(row_items)  # append row
            return data

        print("\t", self.name)  # debug only
        data = get_show_functions()
        for show_function in self.show_functions:  # if there are hidden tables to show
            browser.execute_script(show_function)
            inner_data = self.parse_inner_table(browser)  # get data from table
            data.append([])  # to show there is a inner table
            for row in inner_data:
                data.append(row)  # add to table data

        self.data = data

    # TODO can we remove this method?
    @staticmethod
    def parse_inner_table(browser):
        """
        :param browser: webdriver
            Browser to use.
        :return: list of list
            Raw html table to 2D matrix
        """

        table = BeautifulSoup(browser.page_source, "html.parser").find_all("fieldset")[0]  # find database
        title = html_stripper(table.find_all("h3")[0].text)  # find title
        table = table.find_all("table", {"class": "overview"})[0]  # find table
        data = [[title]]  # add name of section
        for row in table.find_all("tr"):  # cycle through all rows
            data_row = []
            for column_label in row.find_all("th"):  # cycle through all labels
                data_row.append(
                    html_stripper(column_label.text)
                )

            for column in row.find_all("td"):  # cycle through all columns
                data_row.append(
                    html_stripper(column.text)
                )

            data.append(data_row)
        return data


class ESFForm(object):
    """ ESF form in FSG webpage """

    def __init__(self, name, status, show_function):
        """
        :param browser: webdriver
            Browser to use.
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
        self.sections = None  # sections of form

    def get_sections(self, browser):
        """
        :param browser: webdriver
            Browser to use.
        :return: void
            Show this form.
        """

        browser.execute_script(self.show_function)  # go to page of esf form
        WebDriverWait(browser, BROWSER_WAIT_TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.NAME, "submit"))
        )  # wait until fully loaded
        soup = BeautifulSoup(browser.page_source, "html.parser")

        sections = []
        sections_title = soup.find_all("h3")[1:]  # discard first title
        sections_data = soup.find_all("table", {"class": "overview"})
        for i in range(len(sections_title)):  # cycle through all sections
            section = ESFFormSection(
                html_stripper(sections_title[i].text),  # find title
                sections_data[i]  # find table
            )  # create section from raw data

            section.parse(browser)  # parse raw html
            sections.append(section)  # add just found section

        self.sections = sections
        navigate_to_prev_page(browser)  # back of one page in history to restore browser state

        return self.sections


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

        self.form.get_sub_sections()  # get list of form subsections
        for subsection in self.form.sections:
            # TODO now a subsection has the list 'upload_items': dict <key: name of value to upload, value: id of item>
            # find in data file this value, then call browser to put file value into webpage id
            pass


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

    ESF_URL = "https://www.formulastudent.de/esf"

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
            print("Uploading section", section.name)
            self._upload_data_of_section(section)

    def _upload_data_of_section(self, esf_form_section):
        """
        :param esf_form_section: ESFForm
            Esf form section
        :return: void
            Uploads data of selected section
        """

        bot = ESFFormBot(self.browser, esf_form_section)  # build bot to upload single form section7
        # TODO find section file in data folder
        # bot.upload(data_file)


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
