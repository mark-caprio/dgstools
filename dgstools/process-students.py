"""process-students

Generate reports from current student database.

These reports are for general reference, as input to the TA assignment process,
and as working reports to help in preparing research/mentoring committee
assignments.

Requires: PyYAML

The config file "process-students.yml" is a YAML file with the following keys:

    date (str): report date (usually database date) as "mm/dd/yyyy"
    database_filename (str): path to student database snapshot
    faculty_filename (str): path list of current T&TT faculty
    research_committee (bool): make special reports supporting research committee assignments
    research_committee_filename (str): path to spreadsheet giving new committee members
    ta (bool): make special reports supporting TA assignments
    ta_term (str): funding term which should determine ta status ("a"=spring, "b"=fall)

Postprocessing:

    python3 ~/code/dgstools/dgstools/process-students.py

    a2pdfify --plain -f9 student-status-*.txt
    a2pdfify --plain --columns=2 -f9 advising-by-*.txt
    a2pdfify --plain -f10 advising-load-*.txt
    a2pdfify --plain --columns=2 -f10 research-committees-by-faculty-*.txt
    a2pdfify --plain --columns=2 -f12 ta-list-*.txt
    a2pdfify --plain --columns=1 -f12 ta-roster-notes-*.txt
  
Language: Python 3

Mark A. Caprio
University of Notre Dame

09/23/16 (mac): Created (2016b-students).
11/19/16 (mac): Add student status and advising role reports.
01/20/17 (mac): Add advising committee report.
02/04/17 (mac): Add flag for committee chair.  Allow suppression of candidacy status.
08/04/17 (mac): Rename to ???-process-students.py.
02/08/18 (mac): Change precandidacy code to "-".
12/04/18 (mac): Add control break processing to group-advisor listing.
12/17/18 (mac): Adjust handling of year-0 students.
01/06/20 (mac): Expand and consolidate handling of TA roster generation.
01/14/20 (mac): Add "tenured & tenure track" flag on faculty names in advising listings by faculty.
01/18/20 (mac): Add support for research committee assignment proccess.
12/07/21 (mac): Make term agnostic (process-students.py).
02/02/22 (mac): Switch from hard-coded parameters to YAML config file.
08/10/22 (mac): Permit null advisor.

"""

import datetime
import os

import yaml

import spreadsheet

################################################################
# global database configuration
################################################################

# Fields in 20220412_CurrentStudents.csv
# 
#     Last Name
#     First Name
#     Nickname
#     Gender
#     Advisor
#     Committee Member1
#     Committee Member2
#     Committee Member3
#     Committee Research Chair
#     Research Group
#     TheoryExp
#     Year
#     Program
#     GREPhys
#     Invitation to CandidacyYES NO
#     Invitation to Candidacy Date
#     Date Written Candidacy Passed
#     Oral Cand Date
#     Defense Date
#     Fall2122
#     Spring2122
#     ND ID
#     Net ID
#     Research Committee Meeting Date Scheduled2018
#     Research Committee Meeting Date Scheduled2019
#     Research Committee Meeting Date Scheduled2020
#     Research Committee Meeting Date Scheduled2021
#     Research Committee Meeting Date Scheduled2022
#     Experimental Profiency Requirement

field_names = [
    "last",
    "first",
    "nickname",
    "gender",
    "advisor_composite",  # split -> ("advisor","coadvisor")
    "committee1",
    "committee2",
    "committee3",
    "chair",
    "area",
    "theory_expt",
    "year",
    "program",
    "gre_phys",
    "candidacy_invited",
    "candidacy_invitation_date",
    "candidacy_written_date",
    "candidacy_oral_date",
    "defense_date",
    "funding_fall",
    "funding_spring",
    "ndid",
    "netid",
    "meeting_date_prior_year_4",
    "meeting_date_prior_year_3",
    "meeting_date_prior_year_2",
    "meeting_date_prior_year",
    "meeting_date",
    "experimental_proficiency",
]

################################################################
# funding codes
################################################################

TEACHING_STATUS_BY_FUNDING_CODE = {
    # standard
    "TA": True,  # TA funding from GA funds
    "TA-univ": False,  # teaching role supervised and paid by university source (no departmental TA assignment)
    "RA": False,  # RA from advisor's research funds
    "RA-ext": False,  # RA paid directly by external source (e.g., collaborator at national lab)
    "RA-intern": False,  # internship paid directly by external source (c.f. "Fellow-ext")
    "RA-univ": False,  # RA paid by another part of university
    "Fellow-dept": False,  # deparmental endowed fellowship
    "Fellow-univ": False,  # university fellowship (covering base stipend)
    "Fellow-ext": False,  # external fellowship
    "NS": False,  # no support
    "G": False,  # graduated (no support)
    # legacy codes
    "Fellow": False,  # deprecated in favor of specific "Fellow-" code above
    "TA-NA": False,  # TA with no assignment (special GA support, deprecated in favor of "GA")
    "Fellow-remote": False,  # GA funded 20b special arrangement
    # hybrid support
    #
    # TODO: parse slashed support into tokens and eliminate from this dictionary
    "TA/RA": True,
    "RA/Fellow-ext": False,
}

################################################################
# area formatting utility
################################################################

def area_description(area,theory_expt):
    """ Generate plain-language name of research area from database codes.
    """
    
    area_name_by_area = {
        "As" : "Astrophysics",
        "BP" : "Biophysics",
        "CM" : "Condensed matter",
        "HE" : "High energy",
        "NS" : "Network science",
        "NUC" : "Nuclear",
        "" : None
    }

    area_name = area_name_by_area[area]
    if (area=="As" and theory_expt=="Experimental"):
        qualifier = "observation"
    elif (theory_expt=="Experimental"):
        qualifier = "experiment"
    elif (theory_expt=="Theory"):
        qualifier = "theory"
    else:
        qualifier = ""

    return "{} {}".format(area_name,qualifier)

################################################################
# name processing
################################################################

def regularize_name(name,salutation_set={"Prof."}):
    """ Regularize professor name into last-name-first form.

    Processes name in form:
           'Special' (e.g., 'DGS')
           'Last, First [Middle]'
           'First [Middle] Last'
           'Prof. First [Middle] Last'

    Special (i.e., one-word) names are left untouched.

    Arguments:
        name (string) : the name
        salutation_set (set of string, optional) : salutations to strip

    Returns:
        (string) : the regularized name
    """

    tokens = name.split()

    if (len(tokens) == 1):
        # case 'Special'   (e.g., 'DGS')
        regularized_name = name
    elif (tokens[0][-1] == ","):
        # case 'Last, First [Middle]'
        regularized_name = " ".join(tokens)
    elif (tokens[0] in salutation_set):
        # case 'Salutation First [Middle] Last'
        regularized_name = "{}, {}".format(tokens[-1]," ".join(tokens[1:-1]))
    else:
        # case 'First [Middle] Last'
        regularized_name = "{}, {}".format(tokens[-1]," ".join(tokens[0:-1]))

    ## print(name,tokens,regularized_name)

    return regularized_name

################################################################
# status helper functions
################################################################

def get_ta_status_flag(funding_status):
    """Generate TA status flag for student entry.

    This flag is from a "teaching preference request" perspective, not a funding
    perspective.

    Arguments:
        funding_status (str): funding entry for current term

    Returns:
        (str) : flag ("" for non-TA, "*" for TA, or "?" for unrecognized)

    """

    if (len(funding_status.split())==0):
        base_status = ""
    else:
        base_status = funding_status.split()[0]

    base_status_components = base_status.split("/")
    
    if base_status in TEACHING_STATUS_BY_FUNDING_CODE:
        if TEACHING_STATUS_BY_FUNDING_CODE[base_status]:
            # TA
            flag="*"
        else:
            # RA or unfunded or otherwise no teaching duty
            flag=""
    else:
        # fallthrough
        flag="?"

    return flag

def advising_role_str(name,entry):
    """ Generate formatted tag for different advising/committee roles.

    Arguments:
       name (str): Faculty name
       entry (dict): Student entry

    Returns:
        (str): role string
    """

    if (name==entry["advisor"]):
        value = "-- Advisor"
    elif (name==entry["coadvisor"]):
        value = "-- Coadvisor"
    elif (name==entry["chair"]):
        value = "*"
    else:
        value = ""
        
    return value


def supplement_flag_str(name,entry):
    """ Generate flag for newly-assigned committee member.

    Arguments:
       name (str): Faculty name
       entry (dict): Student entry

    Returns:
        (str): flag string
    """

    value = "#" if (name in entry.get("supplement_committee",set())) else ""
    return value

def tenure_flag_str(name,faculty_list):
    """ Generate flag for newly-assigned committee member.

    Arguments:
       name (str): Faculty name
       faculty_list (list of str): T&TT faculty list entry

    Returns:
        (str): flag string
    """

    return "@" if (name in faculty_list) else ""

################################################################
# data input
################################################################

def read_faculty(filename):
    """ Read list of regularized faculty names.

    Arguments:
        filename (str) : filename for input stream

    Returns:
        (list of str) : faculty names
    """

    faculty_stream = open(filename,"r")
    faculty_list = list(faculty_stream)
    faculty_list = list(map(regularize_name,faculty_list))
    return faculty_list

################################################################
# database generation and postprocessing
################################################################

def generate_database(funding_keys, verbose=False):
    """ Read CSV database and postprocess fields.

    Arguments:

        funding_keys (tuple of str): (fall_funding_key,spring_funding_key)

    Returns:

        (list of dict) : list of student records
    """

    # read file
    database = spreadsheet.read_spreadsheet_dictionary(
        database_filename,field_names,
        skip=True,restval="",debug=False
    )

    # postprocess
    for entry in database:

        if verbose:
            print(entry)
            
        # define Last:First key
        entry["key"] = "{last}:{first}".format(**entry)

        # clean up casing
        entry["netid"] = entry["netid"].lower()

        # extract advisor and coadvisor
        advisor_composite=entry["advisor_composite"].strip()
        advisor_split_slash = list(map(str.strip,advisor_composite.split("/")))
        advisor_split_and = list(map(str.strip,advisor_composite.split(" and ")))  # require spaces around "and", else splits on "Randal"!
        if (len(advisor_split_slash)==2):
            # coadvisors, separated by a slash
            advisor_list = advisor_split_slash
        elif (len(advisor_split_and)==2):
            # coadvisors, separated by "and" (legacy)
            advisor_list = advisor_split_and
        elif len(advisor_composite)>0 and advisor_composite != "DGS":
            # no coadvisors, but nonnull string, means just a single advisor
            # (also skip students marked with legacy code "DGS" for student with
            # no research advisor)
            advisor_list = [entry["advisor_composite"]]
        else:
            # no advisor at all
            advisor_list = []
        advisor_list = list(map(regularize_name,advisor_list))  # regularize names
        if len(advisor_list)>=1:
            entry["advisor"] = advisor_list[0]
        else:
            entry["advisor"] = ""
        if (len(advisor_list)==2):
            entry["coadvisor"] = advisor_list[1]
        else:
            entry["coadvisor"] = ""

        # reformatted advisor for brief output
        short_advisor_width = 11
        entry["short_advisor"] = spreadsheet.truncate_string(entry["advisor"].split(",")[0],short_advisor_width)
        entry["short_coadvisor"] = spreadsheet.truncate_string(entry["coadvisor"].split(",")[0],short_advisor_width)
        if (entry["short_coadvisor"]!=""):
            short_advisor_composite = "{}/{}".format(entry["short_advisor"],entry["short_coadvisor"])
        else:
            short_advisor_composite = entry["short_advisor"]
        entry["short_advisor_composite"] = short_advisor_composite

        # reformat student
        short_student_width = 23
        entry["short_student"] = spreadsheet.truncate_string("{last}, {first}".format(**entry),short_student_width)
        if (entry["program"]==""):
            entry["student_year_string"] = "{short_student} ({year})".format(**entry)
        else:
            # special program shows in place of year
            entry["student_year_string"] = "{short_student} ({program})".format(**entry)
        entry["student_email_string"] = "{first} {last} <{netid}@nd.edu>".format(**entry)

        # process committee
        committee = set()
        if (entry["chair"] != ""):
            committee.add(entry["chair"])
        if (entry["committee1"] != ""):
            committee.add(entry["committee1"])
        if (entry["committee2"] != ""):
            committee.add(entry["committee2"])
        if (entry["committee3"] != ""):
            committee.add(entry["committee3"])
        committee = set(map(regularize_name,committee))  # regularize names
        entry["committee"] = committee  # store committee

        # basic status sanity checks
        try:
            float(entry["year"])
        except:
            print("WARN: invalid field value for year for {last}, {first} ({year})".format(**entry))
            
        # candidacy status sanity checks
        if (entry["candidacy_invited"] not in {"No","Yes"}):
            print("WARN: invalid field value for candidacy invitation for {last}, {first} ({candidacy_invited})".format(**entry))
        if (entry["candidacy_invited"]=="Yes"):
            if ((entry["candidacy_invitation_date"]=="")):
                print("WARN: missing candidacy invitation date for {last}, {first}".format(**entry))
        if (entry["candidacy_invited"]=="No"):
            if ((entry["candidacy_invitation_date"]!="") or (entry["candidacy_written_date"]!="") or (entry["candidacy_oral_date"]!="")):
                print("{last}, {first}: candidacy_invited '{candidacy_invited}', candidacy_invitation_date '{candidacy_invitation_date}', "
                      "candidacy_written_date '{candidacy_written_date}', candidacy_oral_date '{candidacy_oral_date}'".format(**entry))
                print("WARN: inconsistent candidacy status for {last}, {first}".format(**entry))

        # candidacy status
        if (entry["defense_date"]!=""):
            status = "D"  # defended completed
        elif (entry["candidacy_oral_date"]!=""):
            status = "C"  # candidacy completed
        elif (entry["candidacy_written_date"]!=""):
            status = "W"  # written complete
        elif (entry["candidacy_invitation_date"]!=""):
            status = "I"  # invited
        else:
            status = " "  # precandidacy

        # extract funding status
        entry["funding_fall"] = entry[funding_keys[0]]
        entry["funding_spring"] = entry[funding_keys[1]]
            
        entry["candidacy_status"] = status

    return database

def augment_committees(database,supplement_filename):
    """ Read CSV database and postprocess fields.

    Format:
        last, first, committee1, committee2, committee3, chair

    Arguments:
        database (list of dict): list of student records
        supplement_filename (str): filename for input stream
    """

    # provide mapping into current database
    database_entry_by_student = {}
    for entry in database:
        database_entry_by_student[entry["key"]] = entry

    # read committee additions file
    supplement_field_names = [
        "last",
        "first",
        "committee1",
        "committee2",
        "committee3",
        "chair",
    ]
    supplement_database = spreadsheet.read_spreadsheet_dictionary(
        supplement_filename,supplement_field_names,
        skip=True,restval="",debug=False
    )

    for supplement_entry in supplement_database:

        # find corresponding entry in main database
        if (supplement_entry["last"] == ""):
            continue
        key = "{last}:{first}".format(**supplement_entry)
        if (key not in database_entry_by_student):
            raise ValueError("Unrecognized student key {} from committee additions database".format(key))
        entry = database_entry_by_student[key]
        
        # process committee supplements
        ## print(supplement_entry)
        supplement_committee = set()
        if (supplement_entry["chair"] != ""):
            supplement_committee.add(supplement_entry["chair"])
            if (entry["chair"] != ""):
                class IonescuError(Exception):
                    def __init__(self, value):
                        self.value = value
                    def __str__(self):
                        return repr(self.value)
                raise IonescuError("too many chairs")
            entry["chair"] = supplement_entry["chair"]
        if (supplement_entry["committee1"] != ""):
            supplement_committee.add(supplement_entry["committee1"])
        if (supplement_entry["committee2"] != ""):
            supplement_committee.add(supplement_entry["committee2"])
        if (supplement_entry["committee3"] != ""):
            supplement_committee.add(supplement_entry["committee3"])
        supplement_committee = set(map(regularize_name,supplement_committee))  # regularize names

        # save results
        entry["supplement_committee"] = supplement_committee
        entry["committee"].update(supplement_committee)


################################################################
# common legends
################################################################

student_status_legend = (
        "Student progress status codes:\n"
        "  [ ] = precandidacy\n"
        "  [I] = invited to take candidacy exam\n"
        "  [W] = written candidacy exam complete\n"
##        "  [C] = candidacy complete (or oral exam scheduled)\n"
        "  [C] = candidacy complete (or oral scheduled)\n"
        "  [D] = defended (or defense scheduled)\n"
)

faculty_legend_base = (
        "  * = out-of-area member / committee chair\n"
    )

faculty_legend_tenure = faculty_legend_base + (
    "  @ = tenured & tenure track (in physics)\n"
    )

################################################################
# sorting helper function
################################################################

def key_kicking_dgs_to_end(name):
    """ Key function to help sort faculty names, putting ""/"DGS"/"TBD" at end of list."""
    return "ZZZZZ"+name if not (" " in name) else name

################################################################
# student status -- sorted report
################################################################

def report_student_status(filename,database,sorting="year",options={},start_year=0):
    """Generate report of student status (including funding).

    Generates "pretty" report by year.

    Arguments:
        filename (str): filename for output stream
        database (list of dict): student database
        sorting (str): "year" for list by year-student, "group-advisor" for group-advisor-year-student (omitting year 1)
        options (set of str): optional fields to include
            (from "support", "area", "meeting", "e-mail")
        start_year (int): starting year to include

    """

    report_stream = open(filename,"w")

    # header
    print(
        "Notre Dame physics graduate students\n"
        "{}\n"
        "\n"
        "{}"
        "\n"
        "".format(DATE_STRING,student_status_legend),
        file=report_stream
    )

    ## if (sorting=="group-advisor"):
    ##     # may not want to count first-years against group
    ##     print(
    ##         "  Report by group and advisor\n"
    ##         "  Includes students starting from year {}".format(start_year),
    ##         file=report_stream
    ##     )

    # generate lines for entries
    tagged_lines = dict()
    tagged_entries = dict()
    last_group = (None,None)
    last_advisor = None
    for entry in database:

        # cut out special students
        ## if (float(entry["year"])==0):
        ##     continue

        if (float(entry["year"])<start_year):
            continue

        # ordering by: decreasing seniority, then alpha
        if (sorting=="year"):
            key = (-float(entry["year"]),entry["last"].upper(),entry["first"].upper())
        elif (sorting=="group-advisor"):
            area_for_sorting = entry["area"] if (entry["area"]!="") else "ZZZ"  # push unafilliated students to end
            key = (area_for_sorting,entry["theory_expt"],entry["advisor"].upper(),
                   -float(entry["year"]),entry["last"].upper(),entry["first"].upper())

        # generate line for entry
        theory_expt_code = entry["theory_expt"][0] if len(entry["theory_expt"])>0 else "";
        ta_status_flag_fall = get_ta_status_flag(entry["funding_fall"])
        ta_status_flag_spring = get_ta_status_flag(entry["funding_spring"])
        tagged_lines[key] = (
            "{student_year_string:28s} {candidacy_status} {short_advisor_composite:20} "
            + ("{area:3} {theory_expt_code:1} " if ("area" in options) else "")
            + ("  {ta_status_flag_fall:1} {funding_fall:20} {ta_status_flag_spring:1} {funding_spring:20}" if ("funding" in options) else "")
            + ("{meeting_date_prior_year_2:10} " if ("meeting" in options) else "")
            + ("{meeting_date_prior_year:10} " if ("meeting" in options) else "")
            + ("{meeting_date:10} " if ("meeting" in options) else "")
            + ("{student_email_string}"  if ("e-mail" in options) else "")
            ).format(
                theory_expt_code=theory_expt_code,
                ta_status_flag_fall=ta_status_flag_fall,ta_status_flag_spring=ta_status_flag_spring,
                **entry
                 )

        # keep track of entry for key
        #
        # needed for control-break processing
        tagged_entries[key] = entry

    # generate sorted output of lines
    for key in sorted(tagged_lines.keys()):

        # control break processing for group-advisor
        entry = tagged_entries[key]
        group = (entry["area"],entry["theory_expt"])
        advisor = entry["advisor"]
        if (sorting=="group-advisor"):
            if (group!=last_group):
                print(
                    "\n"
                    "----------------------------------------------------------------\n"
                    "{}\n"
                    "----------------------------------------------------------------\n"
                    "".format(area_description(entry["area"],entry["theory_expt"])),
                    file=report_stream
                )
            elif (advisor!=last_advisor):
                print("",file=report_stream)
        
        last_advisor = advisor
        last_group = group
        
        # print line
        print(tagged_lines[key],file=report_stream)

    report_stream.close()

################################################################
# student status -- for TA assignment process
################################################################

def report_student_status_for_ta_assignment(filename,database,funding_field,mode):
    """Generate report of student status for ta roster spreadsheet.

    Generates CSV for input to TA assignment machinery (with column
    for TA hours).

    Note: Could use CSV writer machinery instead of format+print.

    Arguments:
        filename (str): filename for output stream
        database (list of dict): student database
        funding_field (str): database field name for funding status
            for current term
        mode (str): selector for roster type
            "list": TA list for distribution to students
            "notes": working form for noting TA preferences during TA assignment
            "spreadsheet": template for roster spreadsheet for input to TA assignment machinery

    """

    report_stream = open(filename,"w")

    # header
    if (mode=="list"):
        print(
            "TA list\n"
            "{}\n"
            "\n"
            "  * = TA support\n"
            "  ? = possible TA support (TBD)\n"
            "".format(DATE_STRING),
            file=report_stream
        )
    elif (mode=="notes"):
        print(
            "                                             |NS|He|Tu|Ex|Ma|La|De|Ob|Gr|Notes\n"
            "                                             +--+--+--+--+--+--+--+--+--+-------",
            file=report_stream
        )
                      
    # generate lines for entries
    tagged_lines = dict()
    for entry in database:

        # cut out special students
        if (float(entry["year"])==0):
            continue

        # ordering by: name-year (which means by name except in extraordinary circumstances)
        key = (entry["last"].upper(),entry["first"].upper(),float(entry["year"]))

        # determine TA hours by heuristic
        funding_status = entry[funding_field]
        if (len(funding_status.split())==0):
            base_status = ""
            status_annotation = ""
        elif (len(funding_status.split())==1):
            base_status = funding_status.split()[0]
            status_annotation = ""
        else:
            base_status = funding_status.split()[0]
            status_annotation = funding_status.split()[1]
        if (base_status in TEACHING_STATUS_BY_FUNDING_CODE and not TEACHING_STATUS_BY_FUNDING_CODE[base_status]):
            # nonteaching role
            hours="0"
        elif (base_status=="TA"):
                if (status_annotation in ["(Schmitt)", "(Notebaert)"] and entry["year"]<="2"):
                    # fellowship TA with reduced hours
                    hours="9"
                else:
                    hours="15"
        else:
            # fallthrough (includes "TA/RA", with hours to be determined manually)
            hours="???"

        # generate line for entry
        ta_status_flag=get_ta_status_flag(entry[funding_field])
        theory_expt_code = entry["theory_expt"][0] if len(entry["theory_expt"])>0 else "";
        if (mode=="list"):
            tagged_lines[key] = (
                "{ta_status_flag:1s} {last}, {first}"
                "".format(ta_status_flag=ta_status_flag,**entry)
            )
        elif (mode=="notes"):
            if (hours!="0"):
                tagged_lines[key] = (
                    "{student_year_string:28s} {very_short_advisor:3s} {area:3s} {theory_expt_code:1} "
                    "{ta_status_flag:1s} {hours:>3s} "
                    "|__|__|__|__|__|__|__|__|__|_______"
                    "".format(
                        very_short_advisor=spreadsheet.truncate_string(entry["short_advisor_composite"],3),
                        theory_expt_code=theory_expt_code,ta_status_flag=ta_status_flag,hours=hours,
                        **entry
                        )
                )
        elif (mode=="spreadsheet"):
            tagged_lines[key] = (
                "{last},{first},{year},{netid},{short_advisor_composite},{area},"
                "{funding_status},{hours},{ta_status_flag}"
                "".format(funding_status=funding_status,hours=hours,ta_status_flag=ta_status_flag,**entry)
            )
        else:
            raise ValueError("Unrecognized mode")

    # generate sorted output of lines
    for key in sorted(tagged_lines.keys()):
        print(tagged_lines[key],file=report_stream)

    report_stream.close()

################################################################
# student status -- as TA list for preference survey
################################################################

def report_student_status_for_ta_list(filename,database,funding_field):
    """Generate TA list for preference survey.

    Arguments:
        filename (str): filename for output stream
        database (list of dict): student database
        funding_field (str): database field name for funding status
            for current term

    """

    report_stream = open(filename,"w")

    # header
    print(
        "TA list\n"
        "{}\n"
        "\n"
        "  * = TA support\n"
        "  ? = possible TA support (TBD)\n"
        "".format(DATE_STRING),
        file=report_stream
    )

    # generate lines for entries
    tagged_lines = dict()
    for entry in database:

        # cut out special students
        if (float(entry["year"])==0):
            continue

        # ordering by: name
        key = (entry["last"],entry["first"],float(entry["year"]))

        # determine TA status
        ta_status_flag = get_ta_status_flag(entry[funding_field])

        # generate line for entry
        tagged_lines[key] = (
            "{ta_status_flag:1s} {last}, {first}"
            "".format(ta_status_flag=ta_status_flag,**entry)
        )

    # generate sorted output of lines
    for key in sorted(tagged_lines.keys()):
        print(tagged_lines[key],file=report_stream)

    report_stream.close()

################################################################
# advising
################################################################

def tally_advising_assignments(database,base_set,count_defended=False):
    """ Tally advising roles by faculty member.

    Arguments:
        database (list of dict) : student database
        base_set (list) : base set of faculty to include, even if unassigned
        count_defended (bool,optional): whether or not to count defended students in current load

    Returns:
        (tuple of dict) : (advisor_tally,coadvisor_tally,committee_tally)
            mapping committee member name to assignment count
    """

    # initialize tallies
    advisor_tally = dict()
    coadvisor_tally = dict()
    committee_tally = dict()
    for member in base_set:
        advisor_tally[member]=0
        coadvisor_tally[member]=0
        committee_tally[member]=0

    for entry in database:

        if ((not count_defended) and (entry["candidacy_status"] == "D")):
            continue

        advisor = entry["advisor"]
        advisor_tally[advisor] = advisor_tally.get(advisor,0)+1

        coadvisor = entry["coadvisor"]
        if (coadvisor != ""):
            coadvisor_tally[coadvisor] = coadvisor_tally.get(coadvisor,0)+1

        for member in entry["committee"]:
            committee_tally[member] = committee_tally.get(member,0)+1

    return (advisor_tally,coadvisor_tally,committee_tally)

def collect_advising_assignments(database,base_set):
    """ Collect advising roles by faculty member.

    Arguments:
        database (list of dict) : student database
        base_set (list) : base set of faculty to include, even if unassigned

    Returns:
        (dict of list of dict) : mapping faculty name to list of student records
    """

    # initialize faculty records
    advising_assignments = dict()
    for member in base_set:
        advising_assignments[member]=[]

    # add entries to faculty records
    for entry in database:

        full_committee = entry["committee"].copy()  # make copy rather than alias
        if (entry["advisor"] != ""):
            full_committee.add(entry["advisor"])
        if (entry["coadvisor"] != ""):
            full_committee.add(entry["coadvisor"])
        
        for member in full_committee:
            advising_assignments[member] = advising_assignments.get(member,[])
            advising_assignments[member].append(entry)

    return advising_assignments

def report_advising_load(filename,database,base_set):
    """ Generate report of advising/coadvising load.

    Arguments:
        filename (str) : filename for output stream
        database (list of dict) : student database
        base_set (list) : base set of faculty to include, even if unassigned
    """

    report_stream = open(filename,"w")

    # header
    print(
        "Advising and research committee loads\n"
        "\n"
        "  {}\n"
        "\n"
        "  advisor + coadvisor / committee\n"
        "  {}"
        "".format(DATE_STRING,faculty_legend_tenure),
        file=report_stream
    )

    (advisor_tally,coadvisor_tally,committee_tally) = tally_advising_assignments(database,base_set)
    # take all faculty names, excluding "DGS"
    sorted_names = sorted(
        (set(advisor_tally.keys()) | set(coadvisor_tally.keys()) | set(committee_tally.keys())),
        key=key_kicking_dgs_to_end
    )
    for name in sorted_names:
        if name in coadvisor_tally:
            coadvisor_tally_string = "+{:1d}".format(coadvisor_tally.get(name,0))
        else:
            coadvisor_tally_string = ""
        print(
            "{:34} {:2d} {:2s} / {:<2d} {:1s}"
            "".format(
                name,advisor_tally.get(name,0),coadvisor_tally_string,committee_tally.get(name,0),
                tenure_flag_str(name,faculty_list)
            ),
            file=report_stream
        )
        ## print(
        ##     "{:31} {:1d} / {:1d} / {:1d}"
        ##     "".format(
        ##         name,advisor_tally.get(name,0),coadvisor_tally.get(name,0),committee_tally.get(name,0)
        ##     ),
        ##     file=report_stream
        ## )
    report_stream.close()

def report_advising_faculty(filename,database,base_set,include_defended=True,include_advising=True,flag_tenured=False):
    """Generate report of advising responsibilities by faculty.

    For "normal" purposes,

        include_defended=True,include_advising=True,flag_tenured=False

    but for new committee assignment purposes (used by recipient for implicit
    assessment of load)

        include_defended=False,include_advising=False,flag_tenured=True

    Arguments:
        filename (str) : filename for output stream
        database (list of dict) : student database
        base_set (list) : base set of faculty to include, even if unassigned
        include_defended (bool,optional): whether or not to list defended students
        include_advising (bool,optional): whether or not to list advising roles

    """

    report_stream = open(filename,"w")

    # header
    if (include_advising):
        title = "Advising and research committees\n  by faculty member\n"
    else:
        title = "Research committees by faculty member\n  excludes defended students\n\n"
    print(
        "{}"
        "{}\n"
        "\n"
        "{}"
        "\n"
        "{}"
        "\n"
        "".format(
            title,DATE_STRING,student_status_legend,
            faculty_legend_tenure if flag_tenured else faculty_legend_base
        ),
        file=report_stream
    )

    # collect advising assignments
    advising_assignments = collect_advising_assignments(database,base_set)

    # sort faculty names, putting "DGS"/"TBD" at end of list
    sorted_names = sorted(advising_assignments.keys(),key=key_kicking_dgs_to_end)
    for name in sorted_names:
        
        # generate lines for entries
        tagged_lines = dict()
        for entry in advising_assignments[name]:

            # assign role
            if (entry["advisor"]==name):
                role = "advisor"
            elif (entry["coadvisor"]==name):
                role = "coadvisor"
            ## elif (entry["chair"]==name):
            ##     role = "chair"
            else:
                role = "committee"

            # prune entries by selection criteria
            if ((not include_defended) and (entry["candidacy_status"] == "D")):
                continue
            if ((not include_advising) and (role not in ["committee","chair"])):
                continue

            # define ordering

            # ordering by: decreasing role, then decreasing seniority, then alpha
            key = (role,-float(entry["year"]),entry["last"],entry["first"])

            # ordering by: decreasing seniority, then alpha
            ##key = (-float(entry["year"]),entry["last"],entry["first"])

            # generate line for entry
            ## student_string = "{last}, {first} ({year})".format(**entry)
            entry_string = "{supplement_flag_str:1s} {student_year_string:28s} [{candidacy_status}] {short_advisor_composite:s} {advising_role_str:9s}".format(
                advising_role_str=advising_role_str(name,entry),
                supplement_flag_str=supplement_flag_str(name,entry),
                **entry
            )
            tagged_lines[key] = entry_string

        # short circuit empty entry
        #   e.g., if include_advising->False and faculty member is only an advisor, not a committee member
        if (len(tagged_lines.keys())==0):
            continue
        
        # head faculty member entry
        print(
            "{:s} {}"
            "".format(
                name,
                tenure_flag_str(name,faculty_list) if flag_tenured else ""
            ),
            file=report_stream
        )
            
        # generate sorted output of lines
        for key in sorted(tagged_lines.keys()):
            print(tagged_lines[key],file=report_stream)

        # buffer line
        print(file=report_stream)

    report_stream.close()

def report_advising_student(filename,database):
    """ Generate report of advising responsibilities by student.

    Arguments:
        filename (str): filename for output stream
        database (list of dict): student database
    """

    report_stream = open(filename,"w")

    # header
    print(
        "Advising and research committees\n  by student\n"
        "\n"
        "  {}\n"
        "\n"
        "{}"
        "".format(DATE_STRING,faculty_legend_base),
        file=report_stream
    )

    # generate lines for entries
    tagged_lines = dict()
    for entry in database:

        # ordering by: name
        key = (entry["last"],entry["first"],float(entry["year"]))

        # generate multiline entry
        ## student_string = "{last}, {first} ({year})".format(**entry)
        ## if (show_candidacy_status):
        ## ##if (show_candidacy_status or (entry["candidacy_status"]=="D")):
        ##     candidacy_status_censored = entry["candidacy_status"]
        ## else:
        ##     candidacy_status_censored = " "
        entry_lines = []
        entry_lines.append("{student_year_string:28s}".format(**entry))
        ordered_full_committee_name_list = []
        if (entry["advisor"]!=""):
            ordered_full_committee_name_list.append(entry["advisor"])
        if (entry["coadvisor"]!=""):
            ordered_full_committee_name_list.append(entry["coadvisor"])
        for name in sorted(entry["committee"]):
            ordered_full_committee_name_list.append(name)
        for name in ordered_full_committee_name_list:
            entry_lines.append(
                "{supplement_flag_str:1s} {name} {advising_role_str:s}".format(
                    name=name,
                    advising_role_str=advising_role_str(name,entry),
                    supplement_flag_str=supplement_flag_str(name,entry),
                    **entry
                )
            )

        tagged_lines[key] = "\n".join(entry_lines)

    # generate sorted output of lines
    for key in sorted(tagged_lines.keys()):
        print(tagged_lines[key],file=report_stream)
        print(file=report_stream)

    report_stream.close()

################################################################
# main program
################################################################

if (__name__=="__main__"):

    # read configuration
    with open("process-students.yml", "r") as f:
        config = yaml.safe_load(f)

    # set date
    date_string = config.get("date")
    month, day, year = tuple(map(int,date_string.split("/")))
    today = datetime.date(year, month, day)
    DATE_STRING = today.strftime("%m/%d/%Y")  # ugly global...
    date_code = today.strftime("%y%m%d")
        
    # read database
    database_filename = config.get("database_filename")
    faculty_filename = config.get("faculty_filename")
    research_committee_filename = config.get("research_committee_filename")
    database = generate_database(funding_keys=("funding_fall","funding_spring"), verbose=False)
    faculty_list = read_faculty(faculty_filename)
    if os.path.exists(research_committee_filename):
        # for preliminary committee assignments
        augment_committees(database,"committee-supplement.csv")

    # student status reports
    report_student_status("student-status-contact-{}.txt".format(date_code),database,options={"area","e-mail"})
    report_student_status(
        "student-status-group-advisor-funding-{}.txt".format(date_code),  # for funding survey and admissions planning
        database,
        options={"area","funding"},sorting="group-advisor",start_year=0.5
    )
    report_student_status(
        "student-status-group-advisor-contact-{}.txt".format(date_code),  # for distribution as ROS contact list
        database,
        options={"area","e-mail"},sorting="group-advisor",start_year=0.5
    )
    ## report_student_status(
    ##     "student-status-group-advisor.txt",  # as candidacy status overview
    ##     database,
    ##     options={"area"},sorting="group-advisor",start_year=0.5
    ## )
    report_student_status("student-status-meeting-{}.txt".format(date_code),database,options={"area","meeting"})

    # advising reports
    report_advising_faculty("advising-by-faculty-{}.txt".format(date_code),database,faculty_list,include_defended=True,include_advising=True,flag_tenured=False)
    report_advising_student("advising-by-student-{}.txt".format(date_code),database)

    # working reports for mentoring committee assignment process (optional)
    make_committee_preparation_reports = config.get("research_committee") is not False
    if (make_committee_preparation_reports):
        report_advising_load("advising-load-{}.txt".format(date_code),database,faculty_list)
        report_advising_faculty("research-committees-by-faculty-{}.txt".format(date_code),database,faculty_list,include_defended=False,include_advising=False,flag_tenured=True)
 
    # working reports for TA assignment process (optional)
    make_ta_assignment_reports = config.get("ta") is not False
    if (make_ta_assignment_reports):
        funding_key_by_term = {"a": "funding_spring", "b": "funding_fall"}
        ta_term = config.get("ta_term")
        current_funding_key = funding_key_by_term[ta_term]
        report_student_status_for_ta_assignment("ta-list-{}.txt".format(date_code),database,current_funding_key,mode="list")
        report_student_status_for_ta_assignment("ta-roster-notes-{}.txt".format(date_code),database,current_funding_key,mode="notes")
        report_student_status_for_ta_assignment("ta-roster-TEMPLATE-{}.csv".format(date_code),database,current_funding_key,mode="spreadsheet")
