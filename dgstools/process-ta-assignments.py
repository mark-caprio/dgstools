""" process-ta-assignments.py

Process TA assignments.

Arguments:

   version (optional) : assignment report version label string

Example:

   python3 process-ta-assignments.py [version]

   a2pdfify --plain -f8 assignments-21a-v?-{course,ta}.txt

Language: Python 3

Mark A. Caprio
University of Notre Dame

07/29/16 (mac): Created (2016b-ta-report.py).
01/03/17 (mac): Update to 17a (2017a-ta-assignment.py).
08/05/17 (mac): Update to 17b (17b-process-ta-assignments.py).
01/07/18 (mac): Update to 18a (18a-process-ta-assignments.py).
07/28/18 (mac): Update to 18b (18b-process-ta-assignments.py).
01/06/19 (mac): Update to 19a (19a-process-ta-assignments.py).
07/15/19 (mac): Update to 19b (19b-process-ta-assignments.py).
01/07/20 (mac): Update to 20a (20a-process-ta-assignments.py).
07/26/20 (mac): Update to 20b (20b-process-ta-assignments.py).
01/20/21 (mac): Update to 21a (21a-process-ta-assignments.py).
08/13/21 (mac): Update to 21b.  Make term agnostic (process-ta-assignments.py).
01/02/22 (mac): Absorb timeslot handling from spreadsheet.py and make more robust.
08/09/22 (mac): Update TA slot fields to new CourseLeaf-based format.  Remove data dumps.
"""

import datetime
import re
import sys

import spreadsheet

################################################################
# global configuration
################################################################

# values for ta field indicating unassigned (see also ta-assignment.txt):
#
# "?": slot to be filled (treated as blank, except flagged as "????????" in
#     report of assignments by course and serves as visual flag
#     in input spreadsheet, as well, more clearly seen in end game)
# "X": intentionally empty slot, for explicit listing as slot
#     (e.g., no support or crosslist)
# ".": hidden reserved slot, to be suppressed on output (e.g., reserved slot for
#     possible filling as resources allow, cleaner than deleting course number
#     to obtain suppression)

TA_EXCLUSION_LIST = [None,"","?","X","."]
TA_SUPPRESSION_LIST = ["."]

# report formatting
REPORT_FIELD_WIDTHS = {
    "title_width" : 25,      # course title (truncated for report line, not header line, seems 30 suffices)
    "instructor_width" : 15, # instructor name (truncated for report line, not header line) 
    "fullname_width" : 28,   # for "Last, First (Year)" output
    "role_width" : 24,       # for TA role, e.g., "Exam Grading"
    "role_width_by_ta" : 21        # ... trimmed shorter so listing by ta doesn't run over
}

# header
REPORT_VERSION_INFO = {
    "term_name" : "Fall 2022",
    "term_code" : "22b",
    "version" : None,
    "date" : None
}

# special treatment of course numbers
#
#   - course numbers alphabetically greater than "PHYS 99900" are used for
#     sorting purposes but printed as X's

COURSE_NONE_THRESHOLD = "PHYS 99900"
COURSE_NONE_TEXT = "PHYS XXXXX"

def course_or_none(course):
    """ Provide special formatting of fictitious course numbers.
    """
    return course if (course<=COURSE_NONE_THRESHOLD) else COURSE_NONE_TEXT

################################################################
# input filters
################################################################

def read_roster(filename):
    """Read and postprocess TA roster table.

    Adds field "key" to each student record for unambiguous indexing based on
    "last:first" (this key can be used to remove ambiguity if the last name is
    not unique).

    Rows with an empty TA name are suppressed.  These may arise, e.g.,
    from a terminal line containing column totals.
    
    Arguments:
        filename (str) : input filename
    
    Returns:
       roster_table (list of dict) : TA records in input order

    """

    # configuration
    field_names = [
        "last","first","year","netid","advisor","area","ta_ra_status",
        "quota",
        "notes"
        ]

    # read file
    roster_table = spreadsheet.read_spreadsheet_dictionary(filename,field_names,skip=False)

    # suppress lines with no name
    roster_table = list(filter((lambda record : record["last"]!=""),roster_table))

    # process fields
    for record in roster_table:
        # convert hours to number
        record["quota"] = int(record["quota"])
        # add fullname key
        record["key"] = "{last}:{first}".format(**record)

    return roster_table

def read_slots(filename):
    """Read and postprocess TA slots table.

    Rows with an empty course number are suppressed.  These may arise,
    e.g., from a terminal line containing column totals.
    
    Arguments:
        filename (str) : input filename
    
    Returns:
       (list of dict) : TA slot records

    """

    # Spreadsheet column headers:
    #
    # Course - Sec,Title,Cr,St,Max,Opn,Xlst,CRN,Instructor,When,Begin,End,Where,
    #
    # Relevant,Exams,Role,Hours,TA,Conflicts,Notes,History

    # The intent is that TA can be identified by "last" if
    # unambiguous, or always by "last:first".

    # configuration
    field_names = [
        # registrar fields
        "course_section",  # broken into "course" and "section" fields in postprocessing
        "title","credits",
        "enrollment_status","enrollment_max","enrollment_open",
        "crosslisted","crn","instructor","when","start_date","end_date","where",
        # add-on fields
        "section_and_when_relevant",  # taken to indicate whether both times and section number are relevant
        "exams","role","hours",
        "ta","conflicts","notes","history"
        ]

    field_names = [
        # registrar CourseLeaf fields (via extract-class-list.py)
        "course","section","crn","enrollment","max_enrollment","xlist","title","instructor","when","where",
        # add-on fields
        "time_relevant","exams","role","hours","ta","conflicts","notes","candidates"
    ]

    # read file
    table = spreadsheet.read_spreadsheet_dictionary(filename,field_names,skip=True,restval="")

    # suppress lines with no course number
    table = list(filter((lambda record : record["course"]!=""),table))

    # convert raw byte strings
    ## table = list(map((lambda),table))

    # process fields
    for record in table:
        ## print(record)

        # split out section number from course number
        #   also clean up any terminal "*" on section number
     
        record["course_or_none"] = course_or_none(record["course"])

        # force section to integer for sorting
        #
        # Otherwise, e.g., section "10" comes lexicographically before section "9".
        if record["section"] == "":
            record["section"] = 0
        else:
            record["section"] = int(record["section"])
        
        # formatted version of section (possibly suppressed)
        record["time_relevant"] = (record["time_relevant"]=="X")
        if (record["time_relevant"]):
            record["section_or_none"] = "{:02d}".format(record["section"])
        else:
            record["section_or_none"] = ""

        # reformat instructor
        #
        # convert slash to ampersand for class with multiple instructors
        record["instructor"] = record["instructor"].replace("/","&")

        # generate reported time
        # 
        # May be reformatted "when" if relevant to assignment, else exam dates if exist.
        if (record["time_relevant"]):
            record["when_or_exams"] = record["when"]
        elif (record["exams"]!=""):
            record["when_or_exams"] = record["exams"]
        else:
            record["when_or_exams"] = ""
        # convert hours to number
        if (record["hours"] in [None,""]):
            record["hours"] = 0  # may occur before spreadsheet is fully populated
        else:
            record["hours"] = int(record["hours"])

    return table

################################################################
# special handling of registrar input fields
#
# for legacy ClassSearch course data (no longer used)
################################################################

def compress_registrar_timeslot_single(timeslot):
    """Compress unnecessary space from *single* registrar class
    schedule timeslot code.

    This is a helper function for internal use by compress_registrar_timeslot.

    """

    # parse raw timeslot
    cleaned = timeslot.strip()
    timeslot_regex = re.compile(r"(?P<days>[MTWRF\s]+) - (?P<time>[\S]+ - [\S]+)")
    match = timeslot_regex.match(cleaned)

    # trap special timeslot values
    if cleaned in {"TBD"}:
        return cleaned
    
    # trap nonstandard timeslot format
    if match is None:
        print("WARN: failed match to date and times in registrar timeslot {}".format(timeslot))
        return cleaned
    
    # convert to short form
    parts = match.groupdict()
    short_days = parts["days"].replace(" ","")
    short_time = parts["time"].replace(" ","")
    short_form = "{short_days} {short_time}".format(short_days=short_days,short_time=short_time)
    return short_form

def compress_registrar_timeslot(timeslot):
    """Compress unnecessary space from registrar class schedule timeslot
    code.

    Multiple times may be delimited by a slash.

    Ex:

    >>> compress_registrar_timeslot("M W F - 11:30A - 12:20P")

    'MWF 11:30A-12:20P'

    >>> compress_registrar_timeslot("W - 3:00P - 3:50P / F - 2:00P - 3:50P")

    'W 3:00P-3:50P / F 2:00P-3:50P'
    """

    timeslot_list = timeslot.split("/")
    short_form_list = list(map(compress_registrar_timeslot_single,timeslot_list))
    short_form = " / ".join(short_form_list)
    return short_form

################################################################
# processing
################################################################

def unique_courses(slots_table):
    """Obtain list of unique courses from slot listing.

    Arguments:
        slots_table (list of dict) : TA slot records
    
    Returns:
        course_list (list of str) : sorted list of course numbers

    """

    # obtain list of unique course numbers
    course_set = set()
    for slot in slots_table:
        course_set.add(slot["course"])
    course_list = list(course_set)
    course_list.sort()

    return course_list

def index_roster(roster_table):
    """Convert roster table to dictionaries for by-student lookup.
    
    The key lookup dictionary provides lookup either by the last name
    or by the key itself.

    The roster dictionary provides only lookup by the key itself.

    One may thus ask for, e.g., 

        student = ta_info_by_ta[key_dict["Fasano"]]
        print(student["hours"])

        student = ta_info_by_ta[key_dict["Fasano:Patrick"]]
        print(student["hours"])

    Arguments:
        roster_table (list of dict) : TA records in input order
    
    Returns:
        ta_keys (list of str) : list of ta keys in input order
        key_dict (dict) : mapping from all accepted ta identifier values (str) to canonical key "last:first" (str)
        ta_info_by_ta (dict) : mapping from canonical key "last:first" (str) to ta record (dict)

    """

    # put each student record into dictionary
    ta_keys = []
    key_dict = {}
    ta_info_by_ta = {}
    for record in roster_table:
        ta_keys.append(record["key"])
        key_dict[record["last"]] = record["key"]
        key_dict[record["key"]] = record["key"]
        ta_info_by_ta[record["key"]] = record

    return ta_keys, key_dict, ta_info_by_ta

def tally_hours(slots_table,ta_keys,key_dict):
    """Accumulate hours on per-TA basis.

    Totals are accumulated by ta key.

    Arguments:
        slots_table (list of dict) : TA slot records
        ta_keys (list of str) : list of ta keys
        key_dict (dict of str) : lookup from ta field value to key

    Returns:
        hours_by_ta (dict) : mapping from key to assigned hours
    """

    # ensure that hours are populated for all known TAs
    hours_by_ta = dict.fromkeys(ta_keys,0)

    # accumulate hours
    for record in slots_table:
        # skip unfilled slot
        if (record["ta"] in TA_EXCLUSION_LIST):
            continue
        # increment hours for TA
        try:
            key = key_dict[record["ta"]]
        except:
            raise ValueError("Unrecognized TA identifier '{}' in entry for course '{}'".format(record["ta"],record["course"]))
        hours_by_ta[key] += record["hours"]
    
    return hours_by_ta

def collect_slots_by_course(slots_table,course_list):
    """Accumulate assigned slots on per-TA basis.

    Slots are accumulated by ta key.

    Arguments:
        slots_table (list of dict) : TA slot records
        course_list (list of str) : sorted list of course numbers

    Returns:
        slots_by_course (dict) : mapping from course number to list of slot records
    """

    # set up repository for slots by course
    # DEBUGGING: beware aliasing to single list instance if use fromkeys
    ## slots_by_course = dict.fromkeys(ta_keys,[])
    slots_by_course = dict()
    for course in course_list:
        slots_by_course[course]=[]

    # accumulate assignments
    for slot in slots_table:
        course = slot["course"]
        slot["course_or_none"] = course_or_none(course)
        slots_by_course[course].append(slot)

    # sort assignments by (course,section)
    for course in course_list:
        slots_by_course[course].sort(key=(lambda slot : (slot["course"],slot["section"])))

    return slots_by_course

def collect_slots_by_ta(slots_table,ta_keys,key_dict,ta_info_by_ta):
    """Accumulate assigned slots on per-TA basis.

    Slots are accumulated by ta key.

    Arguments:
        slots_table (list of dict) : TA slot records
        ta_keys (list of str) : list of ta keys
        key_dict (dict of str) : lookup from ta field value to key
        ta_info_by_ta (dict of dict) : TA records by key

    Returns:
        slots_by_ta (dict) : mapping from key to list of slot records
    """

    # ensure that assignments are populated for all known TAs
    # DEBUGGING: beware aliasing to single list instance if use fromkeys
    ## slots_by_ta = dict.fromkeys(ta_keys,[])
    slots_by_ta = dict()
    for ta in ta_keys:
        slots_by_ta[ta]=[]

    # accumulate assignments
    for slot in slots_table:
        # skip unfilled slot
        if (slot["ta"] in TA_EXCLUSION_LIST):
            continue
        # accumulate assignment for TA
        ta = key_dict[slot["ta"]]
        slots_by_ta[ta].append(slot)

    # sort assignments by (course,section)
    for ta in ta_keys:
        ## print("sorting",ta,len(slots_by_ta[ta]))
        slots_by_ta[ta].sort(key=(lambda slot : (slot["course"],slot["section"])))

    return slots_by_ta


################################################################
# output reports
################################################################

def report_slots_by_course(
        file,ta_info_by_ta,course_list,key_dict,hours_by_ta,slots_by_course,
        show_netid=False,
):
    """Provide report of assignments organized by course.

    Can optionally (with show_netid set to true) generate provide CRN/netid data
    to facilitate reporting TA assignments to registrar.

    Arguments:
        file (stream): output stream
        ta_info_by_ta (dict of dict) : TA records by key
        course_list (list of str) : sorted list of course numbers
        key_dict (dict) : mapping from all accepted ta identifier values (str) to canonical key "last:first" (str)
        hours_by_ta (dict) : mapping from key to assigned hours
        slots_by_course (dict) : mapping from course number to list of slot records
        show_netid (bool, optional): whether or not to report section's CRN
            and TA's netid (to provide to registrar)

    """

    # header
    print(
        "TA assignments {term_name} (by course)\n"
        "Version {version}, {date}\n"
        "".format(**REPORT_VERSION_INFO),
        file=file
    )

    ## print(course_list)
    ## print(slots_by_course.keys())

    for course in course_list:

        # general course info line
        # pick off first slot for this course to obtain general course info
        course_record = slots_by_course[course][0];
        print(
            "{course_or_none} / {title} / {instructor}".format(**course_record),
            file = file
        )

        # enumerate slots
        for slot in slots_by_course[course]:

            fullname = ""
            netid = ""
            crn = slot["crn"]

            # look up TA info
            if (slot["ta"] not in TA_EXCLUSION_LIST):
                ta = key_dict[slot["ta"]]  # only attempt lookup after verified not in exclusion list
                ta_record = ta_info_by_ta[ta];
                fullname = "{last}, {first} ({year})".format(**ta_record)
                netid = ta_record["netid"]
            elif (slot["ta"]=="?"):
                # visually flag "?" case
                fullname = "????????"

            # print entry
            if (slot["ta"] not in TA_SUPPRESSION_LIST):
                netid_field = "  [{:5} / {:8}]".format(crn,netid) if show_netid else ""
                ## netid_field = "  [{:8}]".format(netid) if show_netid else ""
                print(
                    "   "
                    "{course_or_none:9} {section_or_none:2} "
                    "{short_role:{role_width}} {hours:2}   {fullname:{fullname_width}}{netid_field}   {when_or_exams}"
                    "".format(
                        fullname=spreadsheet.truncate_string(fullname,REPORT_FIELD_WIDTHS["fullname_width"]),
                        short_role=spreadsheet.truncate_string(slot["role"],REPORT_FIELD_WIDTHS["role_width"]),
                        short_title=spreadsheet.truncate_string(slot["title"],20),
                        netid_field=netid_field,
                        **spreadsheet.dict_union(slot,REPORT_FIELD_WIDTHS)
                    ),
                file=file
                )
        print(file=file)

def report_slots_by_ta(file,ta_info_by_ta,ta_keys,hours_by_ta,slots_by_ta,mode):
    """Provide report of assignments organized by TA.

    Alternatively (with mode "quota") provides summary of all TAs' hours
    assigned and hour quotas, for assistance in assembling the TA assignments.
    A flag column makrs TAs who are under/approaching/at/over quota.

    Arguments:
        file (stream): output stream
        ta_info_by_ta (dict of dict) : TA records by key
        ta_keys (list of str) : list of ta keys
        hours_by_ta (dict) : mapping from key to assigned hours
        slots_by_ta (dict) : mapping from key to list of slot records
        mode (str): report mode ("quota" or "slots")

    """

    if (mode=="quota"):
        show_hours=True
        list_slots=False
    elif (mode=="slots"):
        show_hours=False
        list_slots=True
    else:
        raise(ValueError("invalid mode argument"))

    # header
    print(
        "TA assignments {term_name} (by TA)\n"
        "Version {version}, {date}\n"
        "".format(**REPORT_VERSION_INFO),
        file=file
    )

    tot_hours = 0
    tot_quota = 0
    for ta in ta_keys:

        # ta name info
        ta_record = ta_info_by_ta[ta];
        fullname = "{last}, {first} ({year})".format(**ta_record)

        # ta hours info
        hours = hours_by_ta[ta]
        quota = ta_record["quota"]
        tot_hours += hours
        tot_quota += quota

        marker = ""
        if (hours == quota):
            marker = "="
        if (hours == quota-1):
            marker = "."  # to address issue of almost-full schedules if reduce exam grading to 2 hours (19b)
        elif (hours > quota):
            marker = "***"

        # suppress TAs
        #
        # criterion:
        # - skip zero-quota TA if unassigned, in quota-reporting mode
        # - skip unassigned TA, in report mode
        #
        # For judging whether or not TA is assigned, go by presence of
        # assigned slots, rather than total assigned hours, since a TA
        # can have 0-hour assignments.
        assigned = (len(slots_by_ta[ta]) > 0)
        if (show_hours):
            if ((quota==0) and not assigned):
                continue
        else:
            if (not assigned):
                continue

        # write TA info line
        if (show_hours):
            print(
                "{fullname:{fullname_width}} {hours:2} / {quota:2} {marker:3}".format(
                    fullname=spreadsheet.truncate_string(fullname,REPORT_FIELD_WIDTHS["fullname_width"]),  # do truncate name in quota report
                    hours=hours,quota=quota,marker=marker,
                    **REPORT_FIELD_WIDTHS
                ),
                file = file
            )
        else:
            print(
                "{fullname:{fullname_width}}".format(
                    fullname=fullname,  # do not truncate name in slots report
                    **REPORT_FIELD_WIDTHS
                ),
                file = file
            )

        # enumerate slots
        if (list_slots):
            for slot in slots_by_ta[ta]:
                print(
                    "   "
                    "{course_or_none:9} {section_or_none:2} {short_title:{title_width}}   {short_instructor:{instructor_width}}   "
                    "{short_role:{role_width_by_ta}} {hours:2}   {when_or_exams}"
                    "".format(
                        short_role=spreadsheet.truncate_string(slot["role"],REPORT_FIELD_WIDTHS["role_width_by_ta"]),
                        short_title=spreadsheet.truncate_string(slot["title"],REPORT_FIELD_WIDTHS["title_width"]),
                        short_instructor=spreadsheet.truncate_string(slot["instructor"],REPORT_FIELD_WIDTHS["instructor_width"]),
                        **spreadsheet.dict_union(slot,REPORT_FIELD_WIDTHS)
                    ),
                file=file
                )
            print(file=file)

    if show_hours:
        # summarize total hours
        print(file=file)
        print("    {:d} assigned / {:d} available".format(tot_hours,tot_quota),file=file)
              
################################################################
# control code
################################################################

def process_database(roster_table,slots_table):
    """Process data into dictionaries.

    For definitions of arguments and return values, see docstrings for
    individual processing functions.

    Arguments:
        roster_table, slots_table

    Returns:
        ta_keys, key_dict, ta_info_by_ta, course_list, hours_by_ta, slots_by_ta, slots_by_course

    """

    # set up ta indexing
    (ta_keys,key_dict,ta_info_by_ta) = index_roster(roster_table)

    # set up course indexing
    course_list = unique_courses(slots_table)

    # process assignments
    hours_by_ta = tally_hours(slots_table,ta_keys,key_dict)
    slots_by_ta = collect_slots_by_ta(slots_table,ta_keys,key_dict,ta_info_by_ta)
    slots_by_course = collect_slots_by_course(slots_table,course_list)
    
    return ta_keys, key_dict, ta_info_by_ta, course_list, hours_by_ta, slots_by_ta, slots_by_course

def prepare_reports(ta_keys, key_dict, ta_info_by_ta, course_list, hours_by_ta, slots_by_ta, slots_by_course):
    """ Generate reports from data as processed into dictionaries.

    For definitions of arguments and return values, see docstrings for
    individual processing functions.

    Arguments:
        ta_keys, key_dict, ta_info_by_ta, course_list, hours_by_ta, slots_by_ta, slots_by_course
        REPORT_VERSION_INFO (dict): term and version information for header

    """
    
    # report by course
    report_filename = "assignments{}-course.txt".format(REPORT_VERSION_INFO["flag"])
    report_stream = open(report_filename,"w")
    report_slots_by_course(report_stream,ta_info_by_ta,course_list,key_dict,hours_by_ta,slots_by_course)
    report_stream.close()

    # report by ta
    report_filename = "assignments{}-ta.txt".format(REPORT_VERSION_INFO["flag"])
    report_stream = open(report_filename,"w")
    report_slots_by_ta(report_stream,ta_info_by_ta,ta_keys,hours_by_ta,slots_by_ta,mode="slots")
    report_stream.close()

    # report by ta -- with netid
    report_filename = "assignments{}-ta-netid.txt".format(REPORT_VERSION_INFO["flag"])
    report_stream = open(report_filename,"w")
    report_slots_by_course(report_stream,ta_info_by_ta,course_list,key_dict,hours_by_ta,slots_by_course,show_netid=True)
    report_stream.close()

    # report hours
    report_filename = "assignments{}-hours.txt".format(REPORT_VERSION_INFO["flag"])
    report_stream = open(report_filename,"w")
    report_slots_by_ta(report_stream,ta_info_by_ta,ta_keys,hours_by_ta,slots_by_ta,mode="quota")
    report_stream.close()
            
################################################################
# main program
################################################################

if (__name__=="__main__"):

    # set up report version info
    # TODO switch to yaml config file
    if (len(sys.argv) > 1):
        REPORT_VERSION_INFO["version"] = sys.argv[1]
        REPORT_VERSION_INFO["flag"] = "-{term_code}-v{version:s}".format(**REPORT_VERSION_INFO)
    else:
        REPORT_VERSION_INFO["version"] = "0"
        REPORT_VERSION_INFO["flag"] = ""
    today = datetime.date.today()
    REPORT_VERSION_INFO["date"] = today.strftime("%m/%d/%Y")

    # read input data
    roster_table = read_roster("ta-roster.csv")
    slots_table = read_slots("ta-assignments.csv")

    # process database
    ta_keys, key_dict, ta_info_by_ta, course_list, hours_by_ta, slots_by_ta, slots_by_course = process_database(roster_table,slots_table)

    # prepare output tabulations
    prepare_reports(ta_keys, key_dict, ta_info_by_ta, course_list, hours_by_ta, slots_by_ta, slots_by_course)

