import numpy as np
import cdms2
import glob


def filterXmls(files, keyMap, crit):
    """
        outList = filterXmls(files, keyMap, crit)

        Function to narrow down the number of xml files in a
        list based on file metadata criteria.

        Inputs:
            files:      list of xml files
            keyMap:     dictionary (xml filenames are keys) which includes
                        the metadata associated with the xml (e.g., ver, cdate,
                        republish, tpoints)
            crit:       string of criteria (e.g., 'tpoints') in which to filter
                        the input list of files

        filterXmls will take the top value(s) from the list. For example, if
        the filter criteria is 'republish' and a list with two republished and
        two unpublished files are passed to the function, the two republished
        files will be returned. The criteria can be boolean or int (will return
        True booleans and the max integer). Alternatively, if the criteria is
        creation date it will return files with the most recent creation date

        If only one file is in the list, the original list is returned (with
        one file).

    """
    if len(files) < 2:
        return files
    # get values
    values = []
    for fn in files:
        v = keyMap[fn][crit]
        values.append(v)
    # determine optimal value
    if type(v) == int:
        vmax = np.max(values)
    else:
        vmax = True
    # create output list
    outList = []
    for fn in files:
        if keyMap[fn][crit] == vmax:
            outList.append(fn)
    return outList


def versionWeight(v):
    """ v = versionWeight(ver)

        versionWeight takes a version string for a CMIP xml and returns a
        numeric in which the larger the number, the more recent the version.
        Typically an int corresponding to the date (e.g., 20190829), but will
        give precedence to version numbers (e.g., v1 is returned as 100000000).
    """
    if v == 'latest':
        v = 0
    else:
        v = int(v.replace('v', ''))
        if v < 10:
            v = v*100000000
    v = int(v)
    return v


def getFileMeta(fn):
    """ cdate, republish, tpoints = getFileMeta(fn)

        getFileMeta takes a filename (fn) for a CMIP xml and returns:
            cdate:      creation date
            republish:  boolean if the underlying data is in the LLNL publish
                        directories
            tpoints:    the number of timesteps in the dataset
    """
    fh = cdms2.open(fn)
    if 'creation_date' in fh.attributes:
        cdate = fh.creation_date
    else:
        cdate = '1989-03-06T17:00:00Z' ; # Assume PCMDI dawn of time
    # If missing, default to PCMDI dawn of time 9am Monday 6th March 1989
    # most dates are of form: 2012-02-13T00:40:33Z
    # some are: Thu Aug 11 22:49:09 EST 2011 - just make 20110101
    if cdate[0].isalpha():
        cdate = int(cdate.split(' ')[-1] + '0101')
    else:
        cdate = int(cdate.split('T')[0].replace('-', ''))
    # check if republished
    if fh.directory.find('publish') > 0:
        republish = True
    else:
        republish = False
    axisList = fh.axes
    if 'time' in axisList.keys():
        tpoints = len(fh['time'])
    else:
        tpoints = 0
    fh.close()
    return cdate, republish, tpoints


def trimModelList(files,
                  criteria=['cdate', 'ver', 'tpoints'],
                  verbose=False):
    """ filesOut = trimModelList(files)

        trimModelList takes in a list of xml files and returns a list of xml
        files such that there is one xml file per model and realization.

        The returned files are priorized by a cascading criteria, which can be
        optionally specified. The default order is:
            cdate:      prioritizes files that were created more recently
            ver:        prioritizes files based on version id
            tpoints:    prioritizes files with more time steps
            republish:  prioritizes files that have 'publish' in their path

        The cascading criteria can be altered by specifying an optional
        argument, criteria, with a list of the strings above (e.g.,
        criteria=['republish', 'tpoints', 'ver', 'cdate']).

        An additional optional argument is verbose (boolean), which will output
        diagnostic information during execution. By default verbose is False.
    """
    keyMap = {}
    models = []
    rips = []
    # loop over files and store metadata
    for fn in files:
        # get metadata for sorting
        model = fn.split('/')[-1].split('.')[4]
        rip = fn.split('/')[-1].split('.')[5]
        ver = versionWeight(fn.split('/')[-1].split('.')[10])
        cdate, republish, tpoints = getFileMeta(fn)
        # collect all models and rips
        models.append(model)
        rips.append(rip)
        # store data in dictionary
        keyMap[fn] = {'model': model, 'rip': rip, 'ver': ver, 'cdate': cdate,
                      'republish': republish, 'tpoints': tpoints}
    # get unique models / rips
    rips = list(set(rips))
    models = list(set(models))
    models.sort()
    rips.sort()

    # loop over each model + realization and filter by /criteria/
    filesOut = []
    for model in models:
        for rip in rips:
            # subset files for each model / realization
            subFiles = [fn for fn in keyMap.keys() if
                        (keyMap[fn]['model'] == model
                            and keyMap[fn]['rip'] == rip)]
            # continue whittling down file list until only one is left
            # by iteratively using each criteria
            for crit in criteria:
                subFiles = filterXmls(subFiles, keyMap, crit)
            # if more than one file is left after criteria is applied,
            # choose first one
            if len(subFiles) > 0:
                filesOut.append(subFiles[0])

    # if verbose mode, print off files and selection (*)
    if verbose:
        # loop over models / rips and see if files are in output list
        # print files used with asterisk and unchosen files next
        for model in models:
            for rip in rips:
                subFiles = [fn for fn in keyMap.keys()
                            if (keyMap[fn]['model'] == model
                                and keyMap[fn]['rip'] == rip)]
                if len(subFiles) > 1:
                    lowFiles = []
                    for fn in subFiles:
                        if fn in filesOut:
                            fn1 = fn
                        else:
                            lowFiles.append(fn)
                    print('* ' + fn1)
                    for fn in lowFiles:
                        print(fn)
                elif len(subFiles) == 1:
                    print('* ' + subFiles[0])

    return filesOut


def getXmlFiles(**kwargs):
    """
        getXmlFiles(**kwargs)

        Function returns a list of xml files based on user-defined search
        criteria (at least one search constraint must be provided). The
        optional arguments, include:

            base : base path to search (default /p/user_pub/xclim/)
            mip_era : mip_era for CMIP data
            activity : activity for CMIP data
            experiment : experiment for CMIP data
            realm : realm for CMIP data
            frequency : frequency for CMIP data
            variable : variable for CMIP data
            model : model for CMIP data
            realization : realization for CMIP data
            gridLabel : grid label for CMIP data
            trim : Boolean to trim off duplicate files (default True)

        Example Usage:
            files = getXmlFiles(model='CCSM4',
                                experiment='historical',
                                variable='tas',
                                mip_era = 'CMIP5',
                                activity = 'CMIP',
                                realm = 'atmos',
                                frequency = 'mon',
                                gridLabel = 'Amon',
                                realization = 'r1i1p1')

        Returns:
            ['/p/user_pub/xclim//CMIP5/CMIP/historical/atmos/mon/tas/CMIP5...
               CMIP.historical.NCAR.CCSM4.r1i1p1.mon.tas.atmos.glb-z1-gu.v20160829.0000000.0.xml']
    """
    #  Define default dictionary
    pathDict = {'base': '/p/user_pub/xclim/',
                'mip_era': '*',
                'activity': '*',
                'experiment': '*',
                'realm': '*',
                'frequency': '*',
                'variable': '*',
                'model': '*',
                'realization': '*',
                'gridLabel': '*',
                'trim': True,
                'verbose': True}

    #  Ensure search arguments were provided
    if len(kwargs.keys()) == 0:
        print('No search criteria provided. Provide search constraints, such as: \n\n'
              'mip_era, activity, experiment, realm, frequency, '
              'variable, model, realization')
        return

    #  Replace default arguments with user-provided arguments
    for key in kwargs:
        if key in pathDict.keys():
            pathDict[key] = kwargs[key]

    #  Construct path to search
    pathString = '{0}/{1}/{2}/{3}/{4}\
                  /{5}/{6}/*.{7}.{8}\
                  .*.{9}.*.xml'.format(pathDict['base'],
                                       pathDict['mip_era'],
                                       pathDict['activity'],
                                       pathDict['experiment'],
                                       pathDict['realm'],
                                       pathDict['frequency'],
                                       pathDict['variable'],
                                       pathDict['model'],
                                       pathDict['realization'],
                                       pathDict['gridLabel'])
    pathString = pathString.replace(' ', '')  # Remove white space

    # Find xml files
    files = glob.glob(pathString)

    #  Trim Model List
    if pathDict['trim']:
        files = trimModelList(files)

    if ((len(files) == 0) & (pathDict['verbose'])):
        print(pathString)

    return files


def findInList(keyString, list):
    """
    find_in_list(keyString, list)

    Intended to subset a list of strings that include a keyword.

    Inputs:
        list:           list of string (e.g., ['tom', 'bob', 'tommy'])
        keyString:      string to check each list entry with (e.g., 'tom')

    Example:

        find_in_list('tom', ['tom', 'bob', 'tommy'])
            returns: ['tom', 'tommy']
    """
    outList = list
    for key in keyString.split('*'):
        outList = [s for s in outList if key in s]

    return outList;
