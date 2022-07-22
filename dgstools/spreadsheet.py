"""spreadsheet.py

Provide CSV file import into simple tabular form.

Requires:

    - unidecode (https://pypi.python.org/pypi/Unidecode)

        % pip install unidecode

Language: Python 3

Mark A. Caprio
University of Notre Dame

07/05/16 (mac): Created.
07/11/16 (mac): Expand response processing options.
07/29/16 (mac): Handle None on input.
09/15/16 (mac): Add more flexibility to tagged lines.
09/23/16 (mac):
  - Rename from google_forms to spreadsheet.
  - Merge in utilities from 2016b-database.
09/25/16 (mac):
  - Add name regularization.
11/09/16 (mac):
  - Add tally_by_field_value.
  - Add replace_newlines option to entry cleanup.
11/17/16 (mac): Read CSV input file into string
  and preprocess before giving to CSV reader.
11/19/16 (mac): Add helper function truncate_string.
11/20/16 (mac): Incorporate unidecode preprocessing on input.
01/06/17 (mac): Add parameter restval to read_spreadsheet_dictionary.
08/13/17 (mac): Extend registrar timeslot handling to slash-separated list.
12/29/19 (mac): Fix handling of null list in split_checkbox_responses.
01/02/22 (mac): Extract specialized helper functions to process-students.py
  and process-ta-assignments.py.

"""

import csv
import io
# import unicodedata
import unidecode
import itertools

import numpy as np

################################################################
# diagnostics
################################################################

def screen_for_special_chars(filename):
    """Read file and flag special characters.
  
    Arguments:
        filename (string) : filename for spreadsheet to open
    """

    with open(filename,mode="r") as infile:
        contents = infile.read(None)
    
    for b in contents:
        if (ord(b)>127):
            print(ord(b))


################################################################
# import functions
################################################################

def clean_up(entry,replace_newlines=True):
    """Clean up field.

    Any empty field is converted from None to a null string.

    Within each field, leading/trailing whitespace are stripped
    (typically stray trailing spaces or newlines), and internal
    newlines are replaced with vertical bars.

    Limitations: The replace_newlines option only applies to string
    values, not lists of strings.

    Arguments:
        entry (str or list or None): value to be cleaned up
        replace_newlines (boolean, optional) : whether or not to replace newlines in entries

    Returns:
       (str or list or None): cleaned-up value

    """
    if (entry is None):
        # case: empty field, read as None
        cleaned = None
    elif (type(entry) is list):
        # case: entries in trailing columns aggregated into list
        # handle recursively
        cleaned = list(map(clean_up,entry))
    else:
        cleaned = entry.strip()
        if (replace_newlines):
            cleaned = cleaned.replace("\n"," | ")
    return cleaned

def read_spreadsheet_clean_stream(filename,skip=False,debug=False):
    """Read CSV spreadsheet into list of dictionaries.

    Arguments:
        filename (string) : filename for spreadsheet to open
        skip (boolean, optional) : whether or not to skip first line

    Return:
        (stream) : cleaned up stream

    """

    # import raw text
    with open(filename,newline="",encoding="utf-8",errors="ignore") as infile:
        if (skip):
            infile.readline()  # skip header line
        contents = infile.read(None)

    # clean up contents
    clean_contents = contents
    clean_contents = unidecode.unidecode(clean_contents)  # convert all unicode to sensible ASCII substitute
    clean_contents = clean_contents.replace(chr(0),"")  # remove NULL (chokes CSV reader)
    clean_stream = io.StringIO(clean_contents)

    return clean_stream

def read_spreadsheet_table(filename,skip=False,debug=False):
    """Read CSV spreadsheet into table of strings.

    Skips first line (header row) and strips leading/trailing
    whitespace from each field (typically stray trailing spaces or
    newlines).
   
    Arguments:
        filename (string) : filename for spreadsheet to open
        skip (boolean, optional) : whether or not to skip first line
        debug (boolean, optional) : whether or not to print debugging
            info on each input line

    Return:
        (list of lists) : table of entries
    """

    clean_stream = read_spreadsheet_clean_stream(filename,skip=skip,debug=debug)

    table = []
    reader = csv.reader(clean_stream)
    for row in reader:
        if (debug):
            print("Row: {}".format(row))
        if (None in row):
            raise(ValueError("Row overruns designated fields"))
        clean_row = list(map(clean_up,row))
        table.append(clean_row)
            
    return table

def read_spreadsheet_dictionary(filename,fieldnames,skip=True,replace_newlines=True,restval=None,debug=False):
    """Read CSV spreadsheet into list of dictionaries.

    By default:

      - Skips first line (header row).

      - Replaces newlines with marker character.
  

    Use of restval="" is recommended for spreadsheets where the
    trailing entry is a text comment which might be missing in some
    lines.

    Arguments:
        filename (string) : filename for spreadsheet to open
        fieldnames (list) : list of field names
        skip (boolean, optional) : whether or not to skip first line
        replace_newlines (boolean, optional) : whether or not to replace newlines in entries
        restval (any, optional) : default value for missing field (pass-through parameter to csv.DictReader)
        debug (boolean, optional) : whether or not to print debugging
            info on each input line

    Return:
        (list of dictionaries) : table of entries

    """

    # clean up input stream
    clean_stream = read_spreadsheet_clean_stream(filename,skip=skip,debug=debug)

    # parse spreadsheet
    reader = csv.DictReader(clean_stream,fieldnames=fieldnames,restval=restval)

    # clean up entries
    data = []
    for entry in reader:
        if (debug):
            print(entry)
        clean_entry = {}
        for field in entry:
            clean_entry[field]=clean_up(entry[field],replace_newlines)
        data.append(clean_entry)

        ## for (key,value) in entry.items():
        ##     print("{} {}",key,value)

            
    return data


################################################################
# field postprocessing
################################################################

def convert_fields_to_flags(dict,keys,padding=" "):
    """Replace contents of nonnull fields with field name.

    This provides for making an easy printed summary of nonnull
    fields, all on one line.

    Intended for processing of form radio buttons generated as a
    one-column "multiple choice grid" in Google forms.

    Arguments:
        dict (dictionary) : dictionary on which to do this substitution
        keys (list) : list of keys to be so replaced
        padding (string,optional) : terminal padding
    
    Example:

        >>> for row in table:
        >>>     google_forms.convert_fields_to_flags(row,boolean_field_names)
        >>> 
        >>> print("Common: {GH}{GW}{GE}{H}{O}\n".format(**row))

        Common: GH GE H 

    """

    for key in keys:
        if (dict[key]!=""):
            dict[key] = key+padding

def convert_fields_to_tagged_lines(dict,keys,prefix="",padding="\n",prune=False):
    """Tag contents of fields with field name, optionally suppressing null
    fields.

    This provides for making an easy printed summary:

    Intended for tagging of open response fields, where optionally
    only nonnull fields need to be printed.
    
    Example:

        >>> for row in table:
        >>>     google_forms.convert_fields_to_tagged_lines(
        >>>         row,tagged_line_field_names,prune=True
        >>>     )
        >>> 
        >>> print("{LT-C}{LT-SP}{LT-G}".format(*row))

    Arguments:
        dict (dictionary) : dictionary on which to do this substitution
        keys (list) : list of keys to be so replaced
        prefix (string,optional) : initial padding
        padding (string,optional) : terminal padding
        prune (boolean, optional) : whether or not to suppress null fields

    """

    for key in keys:
        if (not (prune and (dict[key]==""))):
            dict[key] = "{}{}: {}{}".format(prefix,key,dict[key],padding)

def split_checkbox_responses(dict,keys,delimiter=";",prefix="   ",padding="\n"):
    """Break out comma-delimited responses into indented (or prefixed)
    lines.

    Arguments:
        dict (dictionary) : dictionary on which to do this substitution
        keys (list) : list of keys to be so replaced
        delimiter (string,optional) : checkbox item delimiter on input
        prefix (string,optional) : initial padding
        padding (string,optional) : terminal padding
    """
    for key in keys:
        if (dict[key].strip()==""):
            values = []  # prevent spurious "".split(";") => [""]
        else:
            values = dict[key].split(delimiter)
        values = [
            "{}{}{}".format(prefix,value,padding)
            for value in values
        ]
        dict[key] = "".join(values)

################################################################
# data selection and extraction
################################################################

def filter_by_field(database,key,value_set,negate=False):
    """ Select from a list of records, based on value of field.

    Arguments:
        database (list of dict) : list of database entries
        key (...) : key identifying field of interest
        value_set (set-like) : set of values to filter for
        negate (bool) : whether or not to negate match to value set

    Returns:
        (list) : explicit list of entries
    """
    
    predicate = lambda entry : ((entry[key] in value_set) == (not negate))
    sublist = filter(predicate,database)
    return list(sublist)


def field_values(database,key):
    """ Extract a given field from a list of records.

    Arguments:
        database (list of dict) : list of database entries
        key (...) : key identifying field of interest

    Returns:
        (list) : explicit list of entries
    """
    
    extractor = lambda entry : entry[key]
    values = map(extractor,database)
    return list(values)

def tally_by_field_value(database,key):
    """ Extract a given field from a list of records.

    Arguments:
        database (list of dict) : list of database entries
        key (...) : key identifying field of interest

    Returns:
        (dict) : map (field value) -> (number of occurrences)
    """
    
    extractor = lambda entry : entry[key]
    tally = dict()

    for entry in database:
        value = extractor(entry)
        tally[value] = tally.get(value,0)+1

    return tally

################################################################
# descriptive statistics
################################################################

def list_replace(values,old,new):
    """Replace any occurrence of a given value, in a given list.

    Limitation: Fails to replace np.nan, since == operator yields false
    on nan, and computed nan fails "is" test with np.nan.

    Arguments:
        values (list) : list (or iterable) of input values
        old (...) : old value to be replaced
        new (...) : new value

    Returns:
        (list) : values after replacement

    """

    def replacer(value,old,new):
        if (value==old):
            return new
        else:
            return value

    return list(map((lambda value : replacer(value,old,new)),values))

def list_replace_nan(values,new):
    """ Replace any occurrence nan, in a given list.

    Arguments:
        values (list) : list (or iterable) of input values
        new (...) : new value

    Returns:
        (list) : values after replacement

    >>> list_replace_nan([1,2,np.nan-1],999)
  """

    def replacer(value,new):
        if (np.isnan(value)):
            return new
        else:
            return value

    return list(map((lambda value : replacer(value,new)),values))


def nanmedian(values):
    """ Calculate median excluding nan/inf values.

    Also, empty list is given median value of nan.

    Arguments:
        values (list of numeric values) : the data values

    Returns:
        (numeric) : median or np.nan
    """
 
    filtered_values = list(filter(np.isfinite,values))
    if (len(filtered_values)==0):
        return np.nan

    return np.median(filtered_values)

################################################################
# export functions
################################################################

def write_table(filename,data,format_spec=None,debug=False):
    """ Write table to CSV file.

    Arguments:
        filename (str): Name for outpuf file.
        data (list of list): Data table.
        format (str/list, optional): Format descriptor string or
          list of format descriptor strings (last value used repeatedly).
    """

    with open(filename,"w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if (format_spec is None):
            formatted_data = data
        elif (type(format_spec) == str):
            formatted_data = [
                [
                    format(entry,format_spec)
                    for entry in row
                ]
                for row in data
            ]
        elif (type(format_spec) == list):
            formatted_data = [
                list(itertools.starmap(format,itertools.zip_longest(row,format_spec,fillvalue=format_spec[-1])))
                for row in data
            ]
        else:
            raise(ValueError("format_spec"))

        if (debug):
            print(formatted_data)
        writer.writerows(formatted_data)

################################################################
# helper functions
################################################################

def truncate_string(s,length):
    """ Truncate string to given length.
    """
    return s[0:min(length,len(s))]

def dict_union(*args):
    """ Generate union of dictionaries.

    This helper function is used to combine dictionaries of keyword 
    arguments so that they can be passed to the string format method.

    Arguments:
        *args : zero or more container objects either representing 
             a mapping of key-value pairs or list-like iterable representing
             a list of key-value pairs

    Returns:
       (dict) : the result of successively updating an initially-empty 
           dictionary with the given arguments
    """
    accumulator = dict()
    for dictionary in args:
        accumulator.update(dictionary)
    return accumulator

################################################################
# test code
################################################################

if (__name__ == "__main__"):
    print("Testing...")
    table = np.identity(5)
    table[1,1] = np.nan
    print(table)
    write_table("spreadsheet_test_1.csv",table)
    write_table("spreadsheet_test_2.csv",table,format_spec="f")
    write_table("spreadsheet_test_2.csv",table,format_spec=[".1f","e"])
