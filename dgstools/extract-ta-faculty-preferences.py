"""
extract-ta-faculty-preferences.py

Extract questionnairre responses.

Usage:

  cd ta/22a/forms
  python3 extract-ta-faculty-preferences.py
  a2pdfify -f9 --truncate-lines=no ta-faculty-preferences-22a.txt

Language: Python 3

Mark A. Caprio
University of Notre Dame

07/05/16 (mac): Created.
12/23/16 (mac): Update for 17a.
08/04/17 (mac): Update for 17b.  Write report to file.
12/24/17 (mac): Update for 18a.
07/17/18 (mac): Update for 18b.
12/19/18 (mac): Update for 19a.  Make sorting case insensitive.
07/16/19 (mac): Update for 19b.  Add name listing on output.
12/29/19 (mac): Update for 20a.
07/07/20 (mac): Update for 20b.
01/12/21 (mac): Update for 21a.
07/23/21 (mac): Update for 21b.
12/30/21 (mac): Update for 22a.  Make term agnostic (extract-ta-faculty-preferences).
"""

import spreadsheet

################################################################
# main program
################################################################

# Google spreadsheet column headers (21a):
#
#   "Timestamp"
#   "Username"
#   "Last name"
#   "First name"
#   "Course ID (PHYS XXXXX)"
#   "Course name"
#   "Expected enrollment"
#   "COVID-19 special considerations"  [SPECIAL]
#   "Common TA assignments [HW grading from provided solutions (how often?)]"
#   "Common TA assignments [Written/essay HW grading (how often?)]"
#   "Common TA assignments [Assist in exam grading (how many exams?)]"
#   "Common TA assignments [Evening help or tutorial sessions (how often?)]"
#   "Common TA assignments [Office hours (how many hours per week?)]"
#   "Common TA assignments: Details"
#   "Uncommon TA assignments [Preparing solutions for HW assignments (how often?)]"
#   "Uncommon TA assignments [Preparing solutions for and grading exams (how many exams?)]"
#   "Uncommon TA assignments [Attending lectures (what frequency?)]"
#   "Uncommon TA assignments [Other (describe below)]"
#   "Uncommon TA assignments: Details"
#   "Other specific requests"

# configuration
filename = "Faculty TA preferences (2022A).csv"
report_filename = "ta-faculty-preferences-22a.txt"

field_names = [
    "timestamp","username",
    "last","first",
    "number","name",
    "enrollment",
    "special",
    "GH","GW","GE","H","O","common",  # note HO were combined in TA survey
    "GH-NS","GE-NS","A","X","uncommon",  # caveat: "GH-NS" didn't actually say "grading"
    "other"
]
boolean_field_names = ["GH","GW","GE","H","O","GH-NS","GE-NS","A","X"]

# read file
table = spreadsheet.read_spreadsheet_dictionary(filename,field_names,skip=True)

# filter out test submissions
table = list(filter((lambda row : (row["last"]!="TEST") and (row["name"]!="TEST")),table))

# sort by (lastname, firstname)
table.sort(key=(lambda row : (row["last"].upper(),row["first"].upper())))

# process radio buttons
for row in table:
    spreadsheet.convert_fields_to_flags(row,boolean_field_names)

# generate output tabulation
report_stream = open(report_filename,"w")

# add name summary
submitters = [
    row["last"].title()
    for row in table
]
unique_submitters = sorted(list(set(submitters)))
print("Submitted: {}\n".format(", ".join(unique_submitters)),file=report_stream)
for row in table:
    ## print(row)
    print("{last}, {first}\n"
          "Course: {number} / {name} ({enrollment})\n"
          "Special: {special}\n"  # COVID-19
          "Common: {GH}{GW}{GE}{H}{O}\n"
          "Notes: {common}\n"
          "Uncommon: {GH-NS}{GE-NS}{A}{X}\n"
          "Notes: {uncommon}\n"
          "Other: {other}\n"
          "".format(**row),
          file=report_stream
    )
