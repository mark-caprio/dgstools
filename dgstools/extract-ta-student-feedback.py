"""extract-ta-student-feedback.py

Extract TA end-of-semester feedback questionnairre responses.

Usage:

  cd ta/21b/forms
  python3 extract-ta-student-feedback.py
  a2pdfify -f9 --truncate-lines=no ta-student-feedback-21b.txt

Language: Python 3

Mark A. Caprio
University of Notre Dame

07/11/16 (mac): Created, for 16a.
12/23/16 (mac): Update for 16b.
08/04/17 (mac): Update for 17a.  Write report to file.
12/14/17 (mac): Update for 17b.
05/15/18 (mac): Update for 18a.
12/19/18 (mac): Update for 18b.  Make sorting case insensitive.
05/17/19 (mac): Update for 19a.
12/29/19 (mac): Update for 19b.
05/29/20 (mac): Update for 20a.
12/07/20 (mac): Update for 20b.
01/12/21 (mac): Update for 21a.
12/06/21 (mac): Update to 21b.  Make term agnostic (ta-student-feedback.py).
"""

import spreadsheet

################################################################
# main program
################################################################

# Google spreadsheet column headers (21b...):
#    
#    "Timestamp"
#    "Username"
#    "Last name"
#    "First name"
#    "Course name"
#    "Course number (PHYS XXXXX)"
#    "Lab preparation and setup"
#    "Lab contact hours"
#    "Lab report grading"
#    "Tutorial preparation"
#    "Tutorial contact hours"
#    "Tutorial exercise grading"
#    "Homework grading from provided solutions"
#    "Written/essay homework grading"
#    "Exam grading from provided solutions"
#    "Assisting in proctoring exams (under supervision of instructor)"
#    "Office hours or help sessions"
#    "Homework grading without solutions (and/or preparing homework solutions)"
#    "Exam grading without solutions (and/or preparing exam solutions)"
#    "Proctoring exams without supervision of instructor"
#    "Attending lectures"
#    "Other"
#    "Please share any feedback you may have on the TA responsibilities and the TA assignment process."

response_filename = "Student TA feedback (2021B).csv"
report_filename = "ta-student-feedback-21b.txt"

# configuration
field_names = [
        "timestamp","username",
        "last","first",
        "name","number",
        "Lab-prep","Lab-contact","Lab-grading",
        "Tut-prep","Tut-contact","Tut-grading",
        "HW-grading","Written-grading","Exam-grading","Proctoring","Office-help",
        "HW-grading-NS","Exam-grading-NS","Proctoring-NS","Attending","Other",
        "comments"
    ]
tagged_line_field_names = [
        "Lab-prep","Lab-contact","Lab-grading",
        "Tut-prep","Tut-contact","Tut-grading",
        "HW-grading","Written-grading","Exam-grading","Proctoring","Office-help",
        "HW-grading-NS","Exam-grading-NS","Proctoring-NS","Attending","Other",
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
table.sort(key=(lambda row : (row["last"].upper(),row["first"].upper(),row["timestamp"])))

# process tagged lines buttons
for row in table:
    spreadsheet.convert_fields_to_tagged_lines(
        row,tagged_line_field_names,prune=True
    )

# generate output tabulation
report_stream = open(report_filename,"w")
for row in table:
    print("{last}, {first}\n"
          "Course: {number}\n"
          "{Lab-prep}{Lab-contact}{Lab-grading}"
          "{Tut-prep}{Tut-contact}{Tut-grading}"
          "{HW-grading}{Written-grading}{Exam-grading}{Proctoring}{Office-help}"
          "{HW-grading-NS}{Exam-grading-NS}{Proctoring-NS}{Attending}{Other}"
          "Comments: {comments}\n"
          "".format(**row),
          file=report_stream
    )
