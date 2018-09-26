# !/usr/bin/python3
# coding: utf-8

import argparse

from fsg import fsg


def create_args():
    """
    :return: ArgumentParser
        Parser that handles cmd arguments.
    """

    parser = argparse.ArgumentParser(usage="-u <user to login to FSG website> -p <password to login to FSG website>")
    parser.add_argument("-u", dest="user", help="user to login to FSG website", required=True)
    parser.add_argument("-p", dest="password", help="password to login to FSG website", required=True)
    parser.add_argument("-d", dest="data_folder", help="path to data folder", required=True)
    return parser


def parse_args(parser):
    """
    :param parser: ArgumentParser
        Object that holds cmd arguments.
    :return: tuple
        Values of arguments.
    """

    args = parser.parse_args()
    return str(args.user), str(args.password), str(args.data_folder)


if __name__ == "__main__":
    user, password, data_folder = parse_args(create_args())  # get credentials from command line
    bot = fsg.FSGermanyBot()  # bot to scrape

    print("Logging in...")
    bot.login(user, password)  # login to access members-only data

    print("Getting data to upload...")
    bot.upload_esf(data_folder)

    print("Done!")
    bot.exit()
