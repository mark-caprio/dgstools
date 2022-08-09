"""extract-class-list

Generate class listing from registrar's class list spreadsheet.

Download spreadsheet from Class Search as XLS, then open and resave as CSV.

Requires: PyYAML

The config file "process-students.yml" is a YAML file with the following keys:

    date (str): report date (usually database date) as "mm/dd/yyyy"
    term (str): term as <yyx> ("a"=spring, "b"=fall)
    database_filename (str): path to registrar class spreadsheet (CSV)
    course_blacklist (list of str): course numbers to omit from report

Invocation:

   python3 ~/code/dgstools/dgstools/extract-class-list.py

Language: Python 3

Mark A. Caprio
University of Notre Dame

11/12/16 (mac): Created.
12/06/21 (mac): Update to 22a.  Make term agnostic (extract-class-list.py).
04/12/22 (mac): Switch from hard-coded parameters to YAML config file.
07/22/22 (mac): Switch input from legacy Class Search spreadsheet (before Summer 2022) to CourseLeaf spreadsheet.
07/29/22 (mac): Add output of summary CSV spreadsheet.

"""

import csv
import datetime
import yaml

import spreadsheet

################################################################
# CourseLeaf fields
################################################################

# CourseLeaf fields as of 07/22:

# ,CLSS ID,CRN,Term,Term Code,Department Code,Subject Code,Catalog Number,Course,Section #,
# Course Title,Long Title,Title/Topic,Meeting Pattern,Meetings,Instructor,Room,Status,
# Part of Term,Campus,Inst. Method,Dept. Apr.,Credit Hrs Min,Credit Hrs,Grade Mode,Attributes,
# Course Attributes,Enrollment,Maximum Enrollment,Prior Enrollment,Cross-listings,Cross-list Maximum,
# Internal Memo to the Registrar,Comments (will display in class search)#1,Comments (will display in class search)#2

################################################################
# data input
################################################################

def read_spreadsheet_courseleaf(filename,debug=False):
    """Read CSV spreadsheet from CourseLeaf into list of dictionaries.

    CourseLeaf file format summary:
    
        - First two lines are annotation to skip.

        - Next line is field tags, first field blank.

        - Remaining lines are grouped, with class title in first field of first
          line (to be ignored), and section info in remaining fields of next
          one or more lines.

    Arguments:
        filename (string) : filename for spreadsheet to open
        debug (boolean, optional) : whether or not to print debugging
            info on each input line

    Return:
        (list of dict) : table of entries

    """

    spreadsheet_table = spreadsheet.read_spreadsheet_table(filename,debug=debug)
    

    # read field list
    field_list = spreadsheet_table[2][1:]

    # parse spreadsheet body
    data = []
    for row in spreadsheet_table[3:]:
        if row[0] != "":
            continue
        values = row[1:]
        if debug:
            print(values)
        entry = {}
        for field, value in zip(field_list, values):
            entry[field] = value
        data.append(entry)

    return data

def generate_database(database_filename, course_blacklist=[], debug=False):
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
    courseleaf_data = read_spreadsheet_courseleaf(
        database_filename,
        debug=debug
    )

    # process fields
    data = []
    for courseleaf_entry in courseleaf_data:
        entry = {}

        # copy simple fields
        entry["course"] = courseleaf_entry["Course"]
        entry["section"] = courseleaf_entry["Section #"]
        entry["crn"] = courseleaf_entry["CRN"]
        entry["enrollment"] = courseleaf_entry["Enrollment"]
        entry["max_enrollment"] = courseleaf_entry["Maximum Enrollment"]
        entry["xlist"] = courseleaf_entry["Cross-listings"]
        entry["title"] = courseleaf_entry["Course Title"]
        entry["when"] = courseleaf_entry["Meeting Pattern"]
        entry["where"] = courseleaf_entry["Room"]
        
        # process instructor
        raw_instructor = courseleaf_entry["Instructor"]
        # e.g., "Howk, Chris (JHOWK) [Primary, 50%]; Rudenga, Kristi (KRUDENGA) [50%]"
        raw_instructor_list = raw_instructor.split(";")  # split multiple instructors on semicolon
        instructor_list = []  # collection of "Lastname, Firstname" or TBD
        short_instructor_list = []  # collection of "Lastname" or TBD
        for instructor in raw_instructor_list:
            if instructor.find("To Be Determined") >=0:  # trap TBD instructor
                instructor_list.append("TBD")
                short_instructor_list.append("TBD")
                continue
            last, _, rest = instructor.strip().partition(", ")  # peel off last name
            first, _, _ = rest.partition(" ")  # peel off first name
            instructor_list.append("{}, {}".format(last,first))
            short_instructor_list.append(last)
        entry["instructor"] = " & ".join(instructor_list)
        entry["short_instructor"] = " & ".join(short_instructor_list)
        if entry["course"] in course_blacklist:
            continue
        data.append(entry)
        if debug:
            print(entry)
        
    return data

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
        print(
            "{course} / {title} / {short_instructor} / {when}"
            "".format(**entry),
            file = report_stream
        )
                
            
    report_stream.close()

def generate_course_spreadsheet(filename,database):
    """Generate spreadsheet of course info, as starting point for TA assignments.

    Arguments:
        filename (str) : filename for output stream
        database (list of dict) : student database

    """

    output_fields = [
        "course", "section", "crn", "enrollment", "max_enrollment", "xlist",
        "title", "instructor", "when", "where"
    ]
    
    with open(filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(output_fields)
        
        for entry in database:
            csv_writer.writerow([entry[field] for field in output_fields])
                
            

################################################################
# main program
################################################################

if (__name__=="__main__"):

    # read configuration
    with open("extract-class-list.yml", "r") as f:
        config = yaml.safe_load(f)
    course_blacklist = config["course_blacklist"]

    # set date
    date_string = config.get("date")
    month, day, year = tuple(map(int,date_string.split("/")))
    today = datetime.date(year, month, day)
    date_code = today.strftime("%y%m%d")
    
    # read class schedule
    database_filename = config["database_filename"]
    database = generate_database(database_filename,course_blacklist,debug=False)

    # generate report
    term = config["term"]
    report_filename = "classes-{}-{}.txt".format(term, date_code)
    generate_course_report(report_filename,database)
    spreadsheet_filename = "classes-{}-{}.csv".format(term, date_code)
    generate_course_spreadsheet(spreadsheet_filename,database)
