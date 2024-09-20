"""extract-course-request.py

    Extract responses to faculty course request questionnairre, for
    Instructional & Course Offering Committee.

Usage:

    python3 ~/code/dgstools/dgstools/extract-course-request.py
    a2pdfify --plain --truncate-lines=no -f10 req*.txt

The config file "extract-course-request.yml" is a YAML file with the following keys:

    term (str): term as <yyx> ("a"=spring, "b"=fall)
    response_filename (str): path to form response spreadsheet (CSV)

Requires: PyYAML

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
01/25/23 (mac): Switch from hard-coded parameters to YAML config file.
09/04/23 (mac): Allow form structure (field order) to be specified in config file.
09/06/24 (mac): Rename "requests" field to "comments" and update labeling in output report.

"""

import yaml

import spreadsheet

################################################################
# tools
################################################################

def term_name_from_term(term):
    """ Convert term code as as <yyx> to full term name.

        e.g., "23a" -> "Spring 2023"

    Arguments:

        term (str): term as <yyx> ("a"=spring, "b"=fall)

    Returns:

        (str): term name
    """

    # definitions
    century_stem = "20"
    season_by_code = {"a": "Spring", "b": "Fall"}
                  
    # extract parts of term
    yy = term[:2]
    x = term[-1]

    # build term name
    season = season_by_code[x]
    term_name = "{} {}{}".format(season, century_stem, yy)
    return term_name

    
################################################################
# data input
################################################################

def generate_database(response_filename, prolog, epilog, courses):
    """Read CSV database and postprocess fields.

    Identifying fields:

        timestamp, username, first, last
       
    Special fields:

        continue -- "If you have taught your current course fewer than 3 times
        in the over the past 5 times that it has been offered and have not
        already expressed the desire to change over to a new course, please mark
        below. You do not have to fill the rest of this form."

        agreement -- "If you believe you have reached an understanding with the
        Chair on your teaching assignment for this semester, please remind us of
        the agreement in the space below."

        comments -- "If there is any other comments and/or information that you
        wish to communicate to the Committee, please use the space below."

        other -- (A) "If you would like to teach a new course, or a course not
        listed below, or have any other requests, please list them below." OR
        (B) "If you would like to teach a new course, or a course not listed
        above, please list them below"

    Arguments:

        response_filename (str): filename for input stream

        prolog (str): names of prolog fields (i.e., before courses)

        epilog (str): names of epilog fields (i.e., after courses)

        courses (str): names of courses as appearing in spreadsheet header

    Returns:

       (list of dict) : list of faculty preference records

    """

    # construct full list of field names
    if prolog is None:
        prolog = []
    if epilog is None:
        epilog = []
    field_names = prolog + courses + epilog
    
    # read file
    database = spreadsheet.read_spreadsheet_dictionary(
        response_filename,
        field_names,
        skip=True,debug=False,
    )
    
    # add name (as "last, first") as sorting key
    for entry in database:
        entry["name"] = "{last}, {first}".format(**entry)

    # sort by name
    ## database.sort(key=(lambda entry : entry["name"]))  # can use operator.itemgetter
   
    # process radio buttons
    for entry in database:
        spreadsheet.convert_fields_to_tagged_lines(
            entry, courses,
            prefix="    ",prune=True
        )

    return database

def report_by_faculty(filename, database, term_name, courses):
    """Generate report of preferences by faculty.

    Arguments:

        filename (str): filename for output stream

        database (list of dict): preference database

        term_name (str): formatted term name

        courses (str): names of courses as appearing in spreadsheet header

    """

    report_stream = open(filename,"w")

    # header
    print(
        "Teaching requests by faculty member\n"
        "{term_name}\n"
        "".format(term_name=term_name),
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
            for field_name in courses
        ]
        preference_block = "".join(preference_lines)

        # generate text block for entry
        entry_block = (""
                        "Name: {last}, {first}\n"
                        "Continue? {continue}\n"
                        "Understanding? {agreement}\n"
                        "Comments/info? {comments}\n"
                        "New/other? {other}\n"
                        "{preference_block}"  # string contains all needed newlines
                        "".format(preference_block=preference_block,**entry)
        )
        tagged_blocks[entry["name"].upper()] = entry_block  # force case for sorting purposes

    # generate sorted output
    for key in sorted(tagged_blocks.keys()):
        print(tagged_blocks[key],file=report_stream)

    report_stream.close()


def report_by_course(filename, database, term_name, courses):
    """Generate report of preferences by faculty.

    Arguments:

        filename (str): filename for output stream

        database (list of dict): preference database

        term_name (str): formatted term name

        courses (str): names of courses as appearing in spreadsheet header

    """

    report_stream = open(filename,"w")

    # header
    print(
        "Teaching requests by course\n"
        "{term_name}\n"
        "".format(term_name=term_name),
        file=report_stream
    )

    # generate output tabulation
    tagged_blocks = dict()
    for course_name in courses:

        
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

if (__name__=="__main__"):

    # read configuration
    with open("extract-course-request.yml", "r") as f:
        config = yaml.safe_load(f)
    response_filename = config["response_filename"]
    term = config["term"]
    term_name = term_name_from_term(term)
    prolog = config["prolog"]
    epilog = config["epilog"]
    courses = config["courses"]
    
    # read responses
    database = generate_database(response_filename, prolog, epilog, courses)

    # generate reports
    report_by_faculty("requests-by-faculty-{}.txt".format(term), database, term_name, courses)
    report_by_course("requests-by-course-{}.txt".format(term), database, term_name, courses)
