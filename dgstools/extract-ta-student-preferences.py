"""
extract-ta-student-preferences.py

Extract questionnaire responses.

Usage:

    python3 ~/code/dgstools/dgstools/extract-ta-student-preferences.py
    a2pdfify -f9 --truncate-lines=no ta-student-preferences-*.txt

The config file "extract-ta.yml" is a YAML file with the following keys:

    term (str): term as <yyx> ("a"=spring, "b"=fall)
    response_filename_faculty_preferences (str): path to form response spreadsheet (CSV)
    response_filename_faculty_feedback (str): path to form response spreadsheet (CSV)
    response_filename_student_preferences (str): path to form response spreadsheet (CSV)
    response_filename_student_feedback (str): path to form response spreadsheet (CSV)

Requires: PyYAML

Language: Python 3

Mark A. Caprio
University of Notre Dame

07/11/16 (mac): Created.
12/23/16 (mac): Update for 17a.
08/04/17 (mac): Update for 17b.  Write report to file.
12/24/17 (mac): Update for 18a.
07/24/18 (mac): Update for 18b.
12/19/18 (mac): Update for 19a.  Make sorting case insensitive.
08/10/19 (mac): Update for 19b.
12/29/19 (mac): Update for 20a.
07/23/20 (mac): Update for 20b.
01/12/21 (mac): Update for 21a.
08/08/21 (mac): Update for 21b.
12/30/21 (mac): Update for 22a.  Make term agnostic (extract-ta-student-preferences).
07/22/22 (mac): Switch from hard-coded parameters to YAML config file.

"""

import yaml

import spreadsheet

################################################################
# main program
################################################################

# Google spreadsheet column headers (19a):
#
#   "Timestamp"
#   "Username"
#   "Last name"
#   "First Name"
#   "My preferred type(s) of TA assignments are:"
#   "Class conflicts"
#   "Seminar conflicts"
#   "Additional considerations"
#   "Is there a professor with whom you would have difficulty working?"


if (__name__=="__main__"):

    # read configuration
    with open("extract-ta.yml", "r") as f:
        config = yaml.safe_load(f)
    response_filename = config["response_filename_student_preferences"]
    term = config["term"]
    report_filename = "ta-student-preferences-{}.txt".format(term)
    print("{} -> {}".format(response_filename,report_filename))


    field_names = [
        "timestamp","username",
        "last","first",
        "preferred",
        "class-conflict",
        "sem-conflict",
        "other",
        "exclude"
        ]
    checkbox_newline_field_names = [
        "preferred",
        "class-conflict",
        "sem-conflict",
    ]

    # read responses
    table = spreadsheet.read_spreadsheet_dictionary(
        response_filename,
        field_names,
        skip=True
    )

    # filter out test submissions
    table = list(filter((lambda row : row["last"] not in ["TEST"]),table))

    # sort by (lastname, firstname)
    table.sort(key=(lambda row : (row["last"].upper(),row["first"].upper())))

    # process tagged lines
    for row in table:
        spreadsheet.split_checkbox_responses(
            row,checkbox_newline_field_names
        )

    # generate report tabulation
    report_stream = open(report_filename,"w")
    for row in table:
        ## print(row)
        print("{last}, {first}\n"
              "Preferred types:\n"
              "{preferred}"
              "Conflicts:\n"
              "{class-conflict}"
              "{sem-conflict}"
              "Other: {other}\n"
              "Exclude: {exclude}\n"
              "".format(**row),
              file=report_stream
        )
        #print("{1} {0} <{3}>,".format(*row))
