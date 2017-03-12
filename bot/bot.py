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


import argparse

from .fsg import fsg


def create_args():
    """
    :return: ArgumentParser
        Parser that handles cmd arguments.
    """

    parser = argparse.ArgumentParser(usage="-u <user to login to FSG website> -p <password to login to FSG website>")
    parser.add_argument("-u", dest="user", help="user to login to FSG website", required=True)
    parser.add_argument("-p", dest="password", help="password to login to FSG website", required=True)
    return parser


def parse_args(parser):
    """
    :param parser: ArgumentParser
        Object that holds cmd arguments.
    :return: tuple
        Values of arguments.
    """

    args = parser.parse_args()
    return str(args.user), str(args.password)


if __name__ == "__main__":
    user, password = parse_args(create_args())  # get credentials from command line
    bot = fsg.FSGermanyBot()  # bot to scrape

    print("Logging in...")
    bot.login(user, password)  # login to access members-only data
