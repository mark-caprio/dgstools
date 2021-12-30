"""extract-course-request.py

    Extract responses to faculty course request questionnairre, for
    Instructional & Course Offering Committee.

    Postprocessing:

        python3 extract-course-request.py
        a2pdfify --plain --truncate-lines=no -f10 req*.txt

    Language: Python 3

    Mark A. Caprio
    University of Notre Dame

    09/05/16 (mac): Created (2017a-extract-course-request).
    01/19/17 (mac): Update for 2017b requests.  Add alpha sorting by last name.
    01/23/17 (mac): Add output grouped by course.
    09/04/17 (mac): Update for 18a requests.
    01/22/18 (mac): Update for 18b requests.  Restore "other" field.
    08/11/18 (mac): Update for 19a requests.
    01/22/19 (mac): Update for 19b requests.  Make sorting case insensitive.
    08/26/19 (mac): Update for 20a requests.
    01/24/20 (mac): Update for 20b requests.
    08/25/21 (mac): Update for 21a requests.
    01/29/21 (mac): Update for 21b requests.
    08/29/21 (mac): Update for 22a requests.
    12/30/21 (mac): Make term agnostic (extract-course-request.py).

"""

import spreadsheet

################################################################
# global database configuration
################################################################

# configuration
term = "Spring 2022"
term_tag = "22a"
filename = "210825-ugarg-responses/Spring 2022Course Requests.csv"

# Fields 22a:
# "Timestamp"
# "Your First Name"
# "Your Last Name"
# "If you have taught your current course fewer than 3 times in the last 5 years, please choose from one of the options below:"
# "If you believe you have reached an understanding with the Chair on your teaching assignment for this semester, please remind us of the agreement in the space below."
# "If there is any other comments and/or information that you wish to communicate to the Committee, please use the space below."
# "Phys 10342: Modern Physics: From Quarks to Quasars"
# "PHYS 10310: Engineering Physics I"
# "PHYS 10320: Engineering Physics II"
# "PHYS 20210: Physics for Life Sciences I"
# "PHYS 20220: Physics for Life Sciences II"
# "PHYS 20420: Computational Methods"
# "PHYS 20454: Intermediate Mechanics"
# "PHYS 30472: Electromagnetic Waves"
# "PHYS 50472: Relativity: Special and General "
# "PHYS 50602: Particles and Cosmology"
# "PHYS 50701: Introduction to Nuclear Physics"
# "PHYS 70006: Electrodynamics"
# "PHYS 80004: Quantum Field Theory II"
# "If you would like to teach a new course, or a course not listed above, please list them below"


# Fields 21b:
# "Timestamp"
# "Your First Name"
# "Your Last Name"
# "If you have reached an understanding with the Chair on your teaching assignment for this semester, please remind us of the agreement in the space below."
# "If you have taught your current course fewer than 3 times in the last 5 years, please choose from one of the options below: "
# "If you would like to teach a new course, or a course not listed below, or have any other requests, please list them below."
# "Phys 10033/20333: Earth Focus"
# "Phys 10063/20063: Radioactivity and Society"
# "Phys 10111: Principles of Physics"
# "Phys 10240: Elementary Cosmology"
# "Phys 10320: Engineering Physics II"
# "Phys 20065: Science and Strategy of Nuclear War"
# "Phys 20210: Physics for Life Sciences I"
# "Phys 20220: Physics for Life Sciences II"
# "Phys 20433: Physics C"
# "Phys 20451: Mathematical Methods for Physics I"
# "Phys 20481: Introduction to Astronomy/Astrophysics"
# "Phys 50051: Numerical PDE"
# "Phys 50481: Modern Observational Techniques"
# "Phys 60050: Computational Physics"
# "Phys 60061: Science Writing"
# "Phys 60070: Computing and Data Analysis for Physicists"
# "Phys 60410: Patterns of Life"
# "Phys 70007: Quantum Mechanics I"
# "Phys 80003: Quantum Field Theory I"
#  ""

field_names = [
    "timestamp",
    "first",
    "last",
    "continue",
    "agreement",
    "requests"
]
tagged_line_field_names = [
    "Phys 10342: Modern Physics: From Quarks to Quasars",
    "PHYS 10310: Engineering Physics I",
    "PHYS 10320: Engineering Physics II",
    "PHYS 20210: Physics for Life Sciences I",
    "PHYS 20220: Physics for Life Sciences II",
    "PHYS 20420: Computational Methods",
    "PHYS 20454: Intermediate Mechanics",
    "PHYS 30472: Electromagnetic Waves",
    "PHYS 50472: Relativity: Special and General ",
    "PHYS 50602: Particles and Cosmology",
    "PHYS 50701: Introduction to Nuclear Physics",
    "PHYS 70006: Electrodynamics",
    "PHYS 80004: Quantum Field Theory II",
]
field_names += tagged_line_field_names
field_names += [
    "other"
]

################################################################
# data input
################################################################

def generate_database():
    """ Read CSV database and postprocess fields.

    Returns:
       (list of dict) : list of faculty preference records
    """

    # read file
    database = spreadsheet.read_spreadsheet_dictionary(filename,field_names,skip=True,debug=False)
    
    # add name (as "last, first") as sorting key
    for entry in database:
        entry["name"] = "{last}, {first}".format(**entry)

    # sort by name
    ## database.sort(key=(lambda entry : entry["name"]))  # can use operator.itemgetter
   
    # process radio buttons
    for entry in database:
        spreadsheet.convert_fields_to_tagged_lines(
            entry,tagged_line_field_names,
            prefix="    ",prune=True
        )

    return database

def report_by_faculty(filename,database):
    """Generate report of preferences by faculty.

    Arguments:
        filename (str): filename for output stream
        database (list of dict): preference database
    """

    report_stream = open(filename,"w")

    # header
    print(
        "Teaching requests by faculty member\n"
        "{term}\n"
        "".format(term=term),
        file=report_stream
    )

    # generate output tabulation
    tagged_blocks = dict()
    for entry in database:

        # collect preference lines
        #
        # These will be null strings if empty, or newline terminated
        # if populated, so they can safely be concatenated with no
        # delimiter.

        preference_lines = [
            entry[field_name]
            for field_name in tagged_line_field_names
        ]
        preference_block = "".join(preference_lines)

        # generate text block for entry
        entry_block = (""
                        "Name: {last}, {first}\n"
                        "Didn't ask to change? {continue}\n"
                        "Agreement? {agreement}\n"
                        "Requests? {requests}\n"
                        "Preferences:\n"
                        "{preference_block}"  # string contains all needed newlines
                        "Other: {other}\n"
                        "".format(preference_block=preference_block,**entry)
        )
        tagged_blocks[entry["name"].upper()] = entry_block

    # generate sorted output
    for key in sorted(tagged_blocks.keys()):
        print(tagged_blocks[key],file=report_stream)

    report_stream.close()


def report_by_course(filename,database):
    """Generate report of preferences by faculty.

    Arguments:
        filename (str): filename for output stream
        database (list of dict): preference database
    """

    report_stream = open(filename,"w")

    # header
    print(
        "Teaching requests by course\n"
        "{term}\n"
        "".format(term=term),
        file=report_stream
    )

    # generate output tabulation
    tagged_blocks = dict()
    for course_name in tagged_line_field_names:

        
        # collect preference lines for that course
        preference_lines = dict()
        for entry in database:

            # skip if no preference entered
            if (entry[course_name]==""):
                continue
                
            # extract ranking back out of field
            ranking = entry[course_name].split()[-1]
            name = entry["name"]
            sort_key = (ranking,name.upper())

            preference_lines[sort_key] = "    {name}: {ranking}\n".format(ranking=ranking,**entry)
            
        # generate text block for entry
        preference_block = ""
        for key in sorted(preference_lines.keys()):
            preference_block += preference_lines[key]

        entry_block = ("{course_name}\n"
                       "{preference_block}"  # string contains all needed newlines
                       "".format(course_name=course_name,preference_block=preference_block)
                   )
        tagged_blocks[course_name] = entry_block

    # generate sorted output
    for key in sorted(tagged_blocks.keys()):
        print(tagged_blocks[key],file=report_stream)

    report_stream.close()


################################################################
# main program
################################################################

database = generate_database()
report_by_faculty("requests-by-faculty-{}.txt".format(term_tag),database)
report_by_course("requests-by-course-{}.txt".format(term_tag),database)
