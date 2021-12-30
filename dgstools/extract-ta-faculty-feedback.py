"""
extract-ta-faculty-feedback.py

Extract faculty end-of-semester TA feedback/evaluations.

Usage:

  cd ta/21b/forms
  python3 extract-ta-faculty-feedback.py
  a2pdfify -f9 --truncate-lines=no ta-faculty-feedback-21b.txt

Language: Python 3

Mark A. Caprio
University of Notre Dame

03/20/18 (mac): Created, based on 17b-extract-ta-feedback, for 17b.
05/15/18 (mac): Update for 18a.
12/19/18 (mac): Update for 18b.  Make sorting case insensitive.
05/17/19 (mac): Update for 19a.
12/29/19 (mac): Update for 19b.
05/29/20 (mac): Update for 20a.
12/07/20 (mac): Update for 20b.
01/12/21 (mac): Update for 21a.
12/06/21 (mac): Update to 21b.  Make term agnostic (ta-faculty-feedback.py).

"""

import spreadsheet

################################################################
# main program
################################################################

# Google spreadsheet column headers (21a):
#
#   "Timestamp"
#   "Username"
#   "Course number (PHYS XXXXX)"
#   "Course name"
#   "Last name"
#   "First name"
#   "Role"
#   "Special identifications (optional)"
#   "Comments (to be shared with TA)"

response_filename = "Faculty TA feedback (2021B).csv"
report_filename = "ta-faculty-feedback-21b.txt"

# configuration
field_names = [
    "timestamp","username",
    "number","name",
    "last","first",
    "role","special",
    "comments"
]

# read file
table = spreadsheet.read_spreadsheet_dictionary(
    response_filename,
    field_names,
    skip=True
)

# filter out test submissions
table = list(filter((lambda row : row["last"]!="TEST"),table))

# sort by (lastname, firstname, timestamp)
table.sort(key=(lambda row : (row["last"].upper(),row["first"].upper(),row["number"],row["timestamp"])))

# generate output tabulation
report_stream = open(report_filename,"w")
for row in table:
    ## print(row)
    short_special = row["special"].split(",")[0]
    short_evaluator = row["username"].split("@")[0]
    print("{last}, {first}\n"
          "Course: PHYS {number} / {name} / {username}\n"
          "Role: {role}\n"
          "Special: {short_special}\n"
          "Comments: {comments}\n"
          "".format(short_evaluator=short_evaluator,short_special=short_special,**row),
          file=report_stream
    )
