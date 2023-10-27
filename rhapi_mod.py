from __future__ import print_function

import requests
import re
import json
import sys
from requests.utils import requote_uri
import xml.dom.minidom as minidom
import importlib
"""
Python object that enables connection to RestHub API.
Errors, fixes and suggestions to be sent to project 
website in GitHub: https://github.com/valdasraps/resthub
"""

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RhApiRowCountError(Exception):
    
    def __init__(self, totalRows, fetchedRows):
        self.totalRows = totalRows
        self.fetchedRows = fetchedRows
        
    def __str__(self):
        return 'Total rows count (%d) mismatch with fetched rows count (%d)' % (self.totalRows, self.fetchedRows)


class RhApiRowLimitError(Exception):
    
    def __init__(self, count, rowsLimit):
        self.count = count
        self.rowsLimit = rowsLimit
        
    def __str__(self):
        return 'Rows count (%d) is larger than rows limit (%d) for a single result' % (self.count, self.rowsLimit)

class RhApiPageSizeError(Exception):
    
    def __init__(self, count, rowsLimit, pageSize):
        self.count = count
        self.rowsLimit = rowsLimit
        self.pageSize = pageSize
        
    def __str__(self):
        return 'Page size (%d) is larger than rows limit (%d) for a single result' % (self.pageSize, self.rowsLimit)

class BadColumnNameError(Exception):
    
    def __init__(self, bad_column, columns_list, table_name):
        self.bad_column = bad_column
        self.columns_list = columns_list
        self.table_name = table_name
    def __str__(self):
        return 'Column name (%s) does not exist in the table (%s). Try these columns: (%s).'\
             % (self.bad_column, self.table_name, json.dumps(self.columns_list))

class RhApi:
    """
    RestHub API object
    """

    def __init__(self, url, debug = False, sso = False):
        """
        Construct API object.
        url: URL to RestHub endpoint, i.e. http://localhost:8080/api
        debug: should debug messages be printed out? Verbose!
        sso: use cookie provider from SSO_COOKIE_PROVIDER string
        """
        if re.match("/$", url) is None:
            url = url + "/"
        self.url = url
        self.debug = debug
        self.dprint("url = ", self.url)

        self.cprov = None
        if sso and re.search("^https", url):
            mod_name, fun_name = SSO_COOKIE_PROVIDER.split(":")
            m = importlib.import_module(mod_name)
            self.cprov = getattr(m, fun_name)

    def _action(self, action, url, headers, data):
        force_level = 0
        while True:

            cookies = None
            if self.cprov is not None:
                cookies = self.cprov(self.url, force_level = force_level)

            r = action(url = url, headers = headers, data = data, cookies = cookies, verify = False)

            if r.status_code == 200 and r.url.startswith(SSO_LOGIN_URL):
                if force_level < 2:
                    force_level = force_level + 1
                    continue
                else:
                    if self.cprov is None:
                        raise Exception('Resource is secured by SSO. Please try --sso')
                    else:
                        raise Exception('Error while logging to HTTPS/SSO')

            return r

    def dprint(self, *args):
        """
        Print debug information
        """
        if self.debug: 
            print("RhApi:", end = '')
            for arg in args:
                print(arg, end = '')
            print()

    def get(self, parts, data = None, headers = None, params = None, verbose = False, cols = False, inline_clobs = False, method = None):
        """
        General API call (do not use it directly!)
        """

        if type(params) != dict: params = {}
        if verbose: params["_verbose"] = True
        if cols: params["_cols"] = True
        if inline_clobs: params["_inclob"] = True

        #
        # Constructing request path
        #

        callurl = self.url + "/".join(requote_uri(str(p)) for p in parts)
        callurl = callurl + "?" + "&".join(p + "=" + requote_uri(str(params[p])) for p in params.keys())

        sdata = None
        if data != None:
            sdata = json.dumps(data)

        #
        # Do the query and respond
        #

        self.dprint(callurl, "with payload", sdata, "and headers", headers)

        if method is None:
            if data is None:
                method = 'get'
            else:
                method = 'post'
        else:
            method = method.lower()

        action = getattr(requests, method, None)
        if action:
            resp = self._action(action, headers = headers, url = callurl, data = data)
        else:
            raise NameError('Unknown HTTP method: ' + method)

        self.dprint("Response", resp.status_code, " ".join(str(resp.headers.get('content-type')).split("\r\n")))

        if resp.status_code == requests.codes.ok:
            rdata = resp.text
            if re.search("json", resp.headers.get('content-type')):
                try:
                    return json.loads(rdata)
                except TypeError as e:
                    self.dprint(e)
                    return rdata
            else:
                return rdata
        elif resp.status_code < 300:
            return None
        else:
            raise Exception('Response (' + str(resp.status_code) + '): ' + resp.text)

    def info(self, verbose = False):
        """
        Get server version information
        """
        return self.get(["info"], verbose = verbose)
    
    def folders(self, verbose = False):
        """
        Get list of folders
        """
        return list(self.get(["tables"], verbose = verbose).keys())

    def tables(self, folder, verbose = False):
        """
        Get tables for folder or all
        """
        raw = self.get(["tables"], verbose = verbose)
        d = []
        for t in raw[folder].keys(): 
            d.append(t)
        return d

    def table(self, folder, table, verbose = False):
        """
        Get info for table
        """
        return self.get(["table", folder, table], verbose = verbose)

    def qid(self, query):
        """
        Create query based on [query] and return its ID
        """
        return self.get(["query"], query)

    def query(self, qid, verbose = False):
        """
        Return qid metadata (assuming it exists..)
        """
        return self.get(["query", qid], verbose = verbose)

    def clean(self, qid, verbose = False):
        """
        Remove cache for query (assuming it exists..)
        """
        return self.get(["query", qid, "cache"], verbose = verbose, method = 'DELETE')

    def count(self, qid, params = None, verbose = False):
        """
        Get number of rows in a query 
        """
        return int(self.get(["query", qid, "count"], params = params, verbose = verbose))

    def data(self, qid, params = None, form = 'text/csv', pagesize = None, page = None, verbose = False, cols = False, inline_clobs = False):
        """
        Get data rows
        """

        rowsLimit = self.query(qid, verbose = True)["rowsLimit"]
        count = int(self.count(qid))
        
        ps = ["query", qid]
        if pagesize is None or page is None:
            if count > rowsLimit:
                raise RhApiRowLimitError(count, rowsLimit)
        else:
            if pagesize > rowsLimit:
                raise RhApiPageSizeError(count, rowsLimit, pagesize)
            else:
                ps.extend(["page", pagesize, page]);
                
        ps.append("data")
        return self.get(ps, None, { "Accept": form }, params, verbose = verbose, cols = cols, inline_clobs = inline_clobs)

    def csv(self, query, params = None, pagesize = None, page = None, verbose = False, inline_clobs = False):
        """
        Get rows in CSV format 
        """
        qid = self.qid(query)
        return self.data(qid, params, 'text/csv', pagesize, page, verbose = verbose, inline_clobs = inline_clobs)

    def xml(self, query, params = None, pagesize = None, page = None, verbose = False, inline_clobs = False):
        """
        Get rows in XML format 
        """
        qid = self.qid(query)
        return self.data(qid, params, 'text/xml', pagesize, page, verbose = verbose, inline_clobs = inline_clobs)

    def json(self, query, params = None, pagesize = None, page = None, verbose = False, cols = False, inline_clobs = False):
        """
        Get rows in JSON format (array of arrays)
        """
        qid = self.qid(query)
        return self.data(qid, params, 'application/json', pagesize, page, verbose = verbose, cols = cols, inline_clobs = inline_clobs)
    
    def json_all(self, query, params = None, verbose = False, cols = False, inline_clobs = False):
        """
        Get all rows in JSON format (array of arrays)
        """
        
        rows = []
        
        qid = self.qid(query)     
        rowsLimit = self.query(qid, verbose = True)["rowsLimit"]
        count = int(self.count(qid, params))
        pages = int(count/rowsLimit) + 1
        
        for page in range(1, (pages + 1)):
            data = self.data(qid, params, form="application/json", page = page, pagesize = rowsLimit, verbose = verbose, cols = cols, inline_clobs = inline_clobs)
            rows.extend(data["data"])
        
        if count != len(rows):
            raise RhApiRowCountError(count, len(rows))
        
        return rows
    
    def json2(self, query, params = None, pagesize = None, page = None, verbose = False, cols = False, inline_clobs = False):
        """
        Get rows in JSON2 format (array or objects)
        """
        qid = self.qid(query)
        return self.data(qid, params, 'application/json2', pagesize, page, verbose = verbose, cols = cols, inline_clobs = inline_clobs)

from optparse import OptionParser
import pprint

USAGE = 'usage: %prog [-v] [-u URL] [ FOLDER | FOLDER.TABLE | QUERY ]'
#DEFAULT_URL = "http://vocms00170:2113"
DEFAULT_URL = "http://dbloader-tracker:8113"
DEFAULT_FORMAT = "csv"
DEFAULT_ROOT_FILE = "data.root"
FORMATS = [ "csv", "xml", "json", "json2", "root" ]
SSO_COOKIE_PROVIDER = "cern_sso_api:cern_sso_cookies"
SSO_LOGIN_URL = "https://login.cern.ch/"
QUERY = "select r.run_number from trker_cmsr.trk_ot_test_nextrun_v r"

class CLIClient:
    
    def __init__(self):
        
        self.pp = pprint.PrettyPrinter(indent=4)
        self.parser = OptionParser(USAGE)
        self.parser.add_option("-v", "--verbose",  dest = "verbose",  help = "verbose output. Default: %s" % False, action = "store_true", default = False)
        self.parser.add_option("-u", "--url",      dest = "url",      help = "service URL. Default: %s" % DEFAULT_URL, metavar = "URL", default=DEFAULT_URL)
        self.parser.add_option("-o", "--sso",      dest = "sso",      help = "use cookie provider from cern_sso_api module. Default: %s" % False, metavar = "sso", action = "store_true", default=False)
        self.parser.add_option("-f", "--format",   dest = "format",   help = "data output format for QUERY data (%s). Default: %s" % (",".join(FORMATS), DEFAULT_FORMAT), metavar = "FORMAT", default = DEFAULT_FORMAT)
        self.parser.add_option("-c", "--count",    dest = "count",    help = "instead of QUERY data return # of rows", action = "store_true", default = False)
        self.parser.add_option("-s", "--size",     dest = "size",     help = "number of rows per PAGE return for QUERY", metavar = "SIZE", type="int")
        self.parser.add_option("-g", "--page",     dest = "page",     help = "page number to return. Default 1", metavar = "PAGE", default = 1, type="int")
        self.parser.add_option("-l", "--cols",     dest = "cols",     help = "add column metadata if possible. Default: False", action = "store_true", default = False)
        self.parser.add_option("-b", "--inclob",   dest = "inclob",   help = "inline clobs directly into the output. Default: False (send as links)", action = "store_true", default = False)
        self.parser.add_option("-i", "--info",     dest = "info",     help = "print server version information. Default: False", action = "store_true", default = False)
        self.parser.add_option("-a", "--all",      dest = "all",      help = "force to retrieve ALL data (can take long time). Default: False", action = "store_true", default = False)
        self.parser.add_option("-m", "--metadata", dest = "metadata", help = "do not execute query but dump METADATA. Default: False", action = "store_true", default = False)
        self.parser.add_option("-n", "--clean",    dest = "clean",    help = "clean cache before executing query (new results). Default: False", action = "store_true", default = True)
        self.parser.add_option("-p",               dest = "param",    help = "parameter for QUERY in form -pNAME=VALUE", metavar = "PARAM", action="append")
        self.parser.add_option("-r", "--root",     dest = "root",     help = "ROOT file name, if format set to root. Default: " + DEFAULT_ROOT_FILE, metavar = "ROOT", default=DEFAULT_ROOT_FILE)

    def pprint(self, data):
        self.pp.pprint(data)

    def basicSelect(self, arg, api, param, verbose):
        split_arg = arg.split(".")
        table_metadata = api.table(split_arg[0], split_arg[1], verbose=verbose)
        table_name = split_arg[1]
        # get table names list from meta data
        column_names_list = []
        for i in table_metadata["columns"]:
            column_names_list.append(i["name"])
        
        arg = 'select * from ' + arg + ' a'
        # get and save to list values from p parameters
        params_length = 0
        if param is not None:
            param.sort()
            
        if param:
            param_column_names_list = []
            param_column_value_list = [] 
            split_where = []
            params_length = len(param)
            # assign param values to lists
            for i in param:
                split_where = i.split("=")
                param_column_names_list.append(split_where[0])
                param_column_value_list.append(split_where[1])
            
            # check if value of first parameter belongs to column names                                
            for i in param_column_names_list:
                if i not in column_names_list:
                    raise BadColumnNameError(i, column_names_list, table_name)
                
        if params_length != 0:
            # build where statements            
            previous = next = None
            for index, obj in enumerate(param_column_names_list):
                if index > 0:
                    previous = param_column_names_list[index-1]
                if index < (params_length -1):
                    next = param_column_names_list[index+1]
                if params_length == 1:
                    arg = arg + " where a." + param_column_names_list[index] + " = :" + param_column_names_list[index]                
                else:
                    if index == 0:
                        if param_column_names_list[index] == next:
                            arg = arg + " where (a." + param_column_names_list[index] + " = :" + param_column_names_list[index]
                        else:
                            arg = arg + " where a." + param_column_names_list[index] + " = :" + param_column_names_list[index]
                    else:
                        if previous == param_column_names_list[index]:
                            
                            if param_column_names_list[index] != next:
                                arg = arg + " or a." + param_column_names_list[index] + " = :" + param_column_names_list[index] + str(index) + ")"
                                param[index] = param_column_names_list[index] + str(index) + '=' + param_column_value_list[index]
                            else:
                                arg = arg + " or a." + param_column_names_list[index] + " = :" + param_column_names_list[index] + str(index)
                                param[index] = param_column_names_list[index] + str(index) + '=' + param_column_value_list[index]
                        else:
                            if param_column_names_list[index] != next:
                                arg = arg + " and a." + param_column_names_list[index] + " = :" + param_column_names_list[index]
                            else:
                                arg = arg + " and ( a." + param_column_names_list[index] + " = :" + param_column_names_list[index]                  
                
                previous = next = None
                
        return arg, param

    def run(self):

        try:

            #print ("Args", self.parser.parse_args())
            (options, args) = self.parser.parse_args()
            args = ["select r.run_number from trker_cmsr.trk_ot_test_nextrun_v r"]
            print ("Opts/Args", options, args)

            api = RhApi(options.url, debug = options.verbose, sso = options.sso)

            # Info
            if options.info:
                print("yo")
                self.pprint(api.info(verbose = options.verbose))
                return 0

            # Folders
            if len(args) == 0:
                print("yo1")
                self.pprint(api.folders(verbose = options.verbose))
                return 0

            if len(args) > 1:
                self.parser.error('More than one command found. Maybe double quotes are missing?')
                return 0

            arg = args[0]

            # FOLDER tables
            if re.match("^[a-zA-Z0-9_]+$", arg) is not None:
                print("yo2")
                self.pprint(api.tables(arg, verbose = options.verbose))
                return 0


            # FOLDER.TABLE
            if ((re.match("^[a-zA-Z0-9_]+\\.[a-zA-Z0-9_]+$", arg) is not None) and (options.format is None)):
                print("yo3")
                parts = arg.split(".")
                self.pprint(api.table(parts[0], parts[1], verbose = options.verbose))
                return 0
            
            # if format is Null, assign format to default format
            if options.format is None:
                options.format = DEFAULT_FORMAT
            
            # QUERY
            if re.match("^select ", arg, re.IGNORECASE) is not None or \
            (re.match("^[a-zA-Z0-9_]+\\.[a-zA-Z0-9_]+$", arg) is not None and (options.format is not None)):
                if (re.match("^[a-zA-Z0-9_]+\\.[a-zA-Z0-9_]+$", arg) is not None and (options.format is not None)):
                    arg, options.param = self.basicSelect(arg, api, options.param, options.verbose)                    
                params = {}
                if options.param:
                    for ps in options.param:
                        m = re.match("^([^=]+)=(.*)$", ps)
                        if m:
                            params[m.group(1)] = m.group(2)
                            
                if options.clean:
                    api.clean(api.qid(arg), verbose = options.verbose)

                if options.count:
                    
                    print("test1", api.count(api.qid(arg), params = params, verbose = options.verbose))
                    
                elif options.metadata:
                    
                    qid = api.qid(arg)
                    runNum = self.pprint(api.query(qid, verbose = options.verbose))
                    print(self.pprint(api.query(qid, verbose = options.verbose)))
                    print ("RunNumRhapi", runNum)
                    return runNum
                        
                else:
                    
                    if FORMATS.count(options.format) == 0:
                        
                        self.parser.error('Format %s not understood: please use one of %s' % (options.format, ",".join(FORMATS)))

                    else:
                        
                        if options.size and options.page and options.all:
                            self.parser.error('Wrong combination of options: ALL and SIZE both can not be defined')
                        
                        if options.format == 'csv':
                            try:
                                result = api.csv(arg, params = params, pagesize = options.size, page = options.page, verbose = options.verbose, inline_clobs = options.inclob)
                                runNum = result.split("\n")[1]
                                print ("Run Num", runNum)
                                print("test2", api.csv(arg, params = params, pagesize = options.size, page = options.page, verbose = options.verbose, inline_clobs = options.inclob))
                                return runNum
                            except RhApiRowLimitError as e:
                                if options.all:
                                    page = 0
                                    while (page * e.rowsLimit) < e.count:
                                        page = page + 1
                                        res = api.csv(arg, params = params, pagesize = e.rowsLimit, page = page, verbose = options.verbose, inline_clobs = options.inclob)
                                        if page == 1:
                                            print("test3",res, end = '')
                                        else:
                                            print("test4",'\n'.join(res.split('\n')[1:]), end = '')
                                else:
                                    raise e

                        if options.format == 'xml':
                            try:
                                print(api.xml(arg, params = params, pagesize = options.size, page = options.page, verbose = options.verbose, inline_clobs = options.inclob))
                            except RhApiRowLimitError as e:
                                if options.all:
                                    page = 0
                                    print('<?xml version="1.0" encoding="UTF-8" standalone="no"?><data>', end = '')
                                    while (page * e.rowsLimit) < e.count:
                                        page = page + 1
                                        res = api.xml(arg, params = params, pagesize = e.rowsLimit, page = page, verbose = options.verbose, inline_clobs = options.inclob)
                                        root = minidom.parseString(res).documentElement
                                        for row in root.getElementsByTagName('row'):
                                            print(row.toxml(), end = '')
                                    print('</data>')
                                else:
                                    raise e

                        if options.format in ['json','json2','root']:
                            try:
                                method_name = options.format if options.format != 'root' else 'json'
                                method = getattr(api, method_name, None)
                                in_cols = options.cols if options.format != 'root' else True
                                data = method(arg, params = params, pagesize = options.size, page = options.page, verbose = options.verbose, cols = in_cols, inline_clobs = options.inclob)
                            except RhApiRowLimitError as e:
                                if options.all:
                                    page = 0
                                    data = None
                                    while (page * e.rowsLimit) < e.count:
                                        page = page + 1
                                        res = method(arg, params = params, pagesize = e.rowsLimit, page = page, verbose = options.verbose, cols = in_cols, inline_clobs = options.inclob)
                                        if data is None:
                                            data = res
                                        else:
                                            data['data'].extend(res['data'])
                                else:
                                    raise e

                            if options.format == 'root':
                                self._to_root(data, options.root)
                            else:
                                print("test4",data)
                        
                return 0

            self.parser.error('Command %s not understood' % arg)

        except RhApiRowLimitError as e:
            
            print("ERROR: %s\nDetails: %s, consider --all option" % (type(e).__name__, e))

        except requests.exceptions.RequestException as e:
            reason = e.reason if hasattr(e, 'reason') else '%s' % e
            print("ERROR: %s\nDetails: %s" % (reason, e))
            
        except Exception as e:
            
            print("ERROR: %s\nDetails: %s" % (type(e).__name__, e))
            import traceback
            traceback.print_exc()

    def _root_column(self, data, ci, ct, cn):

        type_mapping = {
            str:   'Char_t',
            int:   'Int_t',
            float: 'Float_t'
        }

        if ct == 'NUMBER':
            t = int
            for r in data['data']:
                if r[ci] is not None and type(r[ci]) == float:
                    t = float
                    break
            return type_mapping[t] + ' ' + cn
        else:
            l = 1
            for r in data['data']:
                if r[ci] is None:
                    r[ci] = ''
                elif len(r[ci]) > l:
                    l = len(r[ci])
            return type_mapping[str] + ' ' + cn + '[' + str(l) + ']'

    def _to_root(self, data, filename):

        import ROOT
        from ROOT import TFile, TTree, gROOT, AddressOf

        columns = [ self._root_column(data, i, c['type'], c['name']) for i,c in enumerate(data['cols']) ]
        header = 'struct data_t { ' + ';'.join(columns) + '; };'

        gROOT.ProcessLine(header)
        row = ROOT.data_t()
        f = TFile(filename, 'RECREATE')
        tree = TTree('data', 'data from RHAPI')
        tree.Branch('data', row)

        for r in data['data']:
            for i, c in enumerate(data['cols']):
                v = r[i]
                if v is None:
                    if c['type'] == 'NUMBER': v = -1
                    else: v = ''
                try:
                    setattr(row, c['name'], v)
                except Exception as e:
                    print(c['name'], '=', v)
                    print(c, v)
                    print(e)
            tree.Fill()

        tree.Print()
        tree.Write()

if __name__ == '__main__':

    cli = CLIClient()
    sys.exit(cli.run())

