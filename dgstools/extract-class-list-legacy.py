"""extract-class-list-legacy

Generate class listing from registrar's class list spreadsheet.

Download spreadsheet from Class Search as XLS, then open and resave as CSV.

Requires: PyYAML

The config file "process-students.yml" is a YAML file with the following keys:

    date (str): report date (usually database date) as "mm/dd/yyyy"
    term (str): term as <yyx> ("a"=spring, "b"=fall)
    database_filename (str): path to registrar class spreadsheet (CSV)

Limitations:

    - Multiple instructors for a course are dropped.

Invocation:

   python3 ~/code/dgstools/dgstools/extract-class-list-legacy.py

Language: Python 3

Mark A. Caprio
University of Notre Dame

11/12/16 (mac): Created.
12/06/21 (mac): Update to 22a.  Make term agnostic (extract-class-list.py).
04/12/22 (mac): Switch from hard-coded parameters to YAML config file.
07/22/22 (mac): Branch off extract-class-list-legacy for legacy Class Search spreadsheet (before Summer 2022).
"""

import datetime
import yaml

import spreadsheet

################################################################
# global database configuration
################################################################

# Fields in database:
#
# Course - Sec Title	Cr	St	Max	Opn	Xlst	CRN	Instructor	When	Begin	End	Where

# configuration
field_names = [
    "course-section",  # broken into "course" and "section" fields in postprocessing
    "title","credits","status","max","open","crosslist","crn",
    "instructor","when","begin","end","where"
]

################################################################
# data input
################################################################

def generate_database(database_filename):
    """ Read CSV database and postprocess fields.

    Arguments:

        database_filename (str): past to registrar class schedule spreadsheet (CSV)

    Generated fields:

        course
        section

    Returns:
       (list of dict) : list of student records
    """

    # read file
    database = spreadsheet.read_spreadsheet_dictionary(
        database_filename,field_names,
        skip=True,debug=False
    )

    # process fields
    for entry in database:
        # split out section number from course number
        #   also clean up any terminal "*" on section number
        course_section_parts = entry["course-section"].split("-")
        entry["course"] = course_section_parts[0]
        entry["section"] = ""
        if len(course_section_parts)>1:
            entry["section"] = course_section_parts[1]
        entry["section"] = entry["section"].rstrip("*")

    return database

################################################################
# reports
################################################################

def generate_course_report(filename,database):
    """ Generate report of course/title/when.

    Arguments:
        filename (str) : filename for output stream
        database (list of dict) : student database
    """

    report_stream = open(filename,"w")

    for entry in database:
        short_instructor = entry["instructor"].split(",")[0]
        print(
            "{course} / {title} / {short_instructor} / {when}"
            "".format(short_instructor=short_instructor,**entry),
            file = report_stream
        )
                
            
    report_stream.close()

################################################################
# main program
################################################################

if (__name__=="__main__"):

    # read configuration
    with open("extract-class-list-legacy.yml", "r") as f:
        config = yaml.safe_load(f)

    # set date
    date_string = config.get("date")
    month, day, year = tuple(map(int,date_string.split("/")))
    today = datetime.date(year, month, day)
    date_code = today.strftime("%y%m%d")

    # read class schedule
    database_filename = config["database_filename"]
    database = generate_database(database_filename)

    # generate report
    term = config["term"]
    report_filename = "classes-{}-{}.txt".format(term, date_code)
    generate_course_report(report_filename,database)
