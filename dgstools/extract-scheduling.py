""" Extract scheduling responses from survey form.

Usage:

    python3 ~/code/dgstools/dgstools/extract-scheduling.py
    a2pdfify -f10 --landscape *-scheduling.txt

The config file "extract-scheduling.yml" is a YAML file with the following keys:

    response_filename (str): path to form response spreadsheet (CSV)
    report_filename (str): path to summary report
    dates (list of str): strings representing dates
    response_codes (dict): translation from Google response text to single-character visual code for response
    name_width (int, optional): width for name column
    date_width (int, optional): width for each date column

Requires: PyYAML

Language: Python 3

Mark A. Caprio
University of Notre Dame

08/06/22 (mac): Created (from extract-ta-student-preferences.py).

"""

import yaml

import spreadsheet

################################################################
# main program
################################################################

# Example Google spreadsheet column headers:
#
#     "Timestamp"
#     "Username"
#     "Last name"
#     "First name"
#     "Availability [August 23]"
#     "Availability [August 30]"
#     "Availability [September 6]"
#     "Availability [September 13]"
#     "Availability [September 20]"
#     "Availability [September 27]"
#     "Availability [October 4]"
#     "Availability [October 11]"
#     "Availability [October 25]"
#     "Availability [November 1]"
#     "Availability [November 8]"
#     "Availability [November 15]"
#     "Availability [November 22]"
#     "Availability [November 29]"
#     "Availability [December 6]"
#     "Comments"

if (__name__=="__main__"):

    # read configuration
    with open("extract-scheduling.yml", "r") as f:
        config = yaml.safe_load(f)
    response_filename = config["response_filename"]
    report_filename  = config["report_filename"]
    print("{} -> {}".format(response_filename,report_filename))
    dates = config["dates"]
    name_width = config.get("name_width",20)
    date_width = config.get("date_width",6)
    response_codes = config["response_codes"]

    # read responses
    field_names = [
        "timestamp","username",
        "last","first",
    ]
    field_names += dates
    field_names += [
        "comments",
    ]
    table = spreadsheet.read_spreadsheet_dictionary(
        response_filename,
        field_names,
        skip=True
    )

    # filter out test submissions
    table = list(filter((lambda row : row["last"] not in ["TEST"]),table))

    # sort by (lastname, firstname)
    table.sort(key=(lambda row : (row["last"].upper(),row["first"].upper())))

    # generate report tabulation
    report_stream = open(report_filename,"w")

    # generate header line
    entries = ["{:{}} ".format("", name_width)]
    for date in dates:
        entries.append("{:{}s}".format(date,date_width))
    output_line = "".join(entries)
    print(output_line,file=report_stream)

    # generate respondent rows
    for row in table:
        ## print(row)
        full_name = "{last}, {first}".format(**row)
        entries = ["{:{}} ".format(full_name, name_width)]
        for date in dates:
            entries.append("{:{}s}".format(response_codes[row[date]],date_width))
        entries.append("{comments}".format(**row))
        output_line = "".join(entries)
        print(output_line,file=report_stream)
