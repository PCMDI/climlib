import numpy as np
import cdms2


def filterXmls(files, keyMap, crit):
    """
        outList = filterXmls(files, keyMap, crit)

        Function to narrow down the number of xml files in a
        list based on file metadata and a metadata criteria.

        Inputs:
            files:      list of xml files
            keyMap:     dictionary (xml filenames are keys) which includes
                        the metadata associated with the xml (e.g., ver, cdate,
                        publish, tpoints)
            crit:       string of criteria (e.g., 'tpoints') in which to filter
                        the input list of files

        filterXmls will take the top value(s) from the list. For example, if
        the filter critera is 'publish' and a list with two published and two
        unpublished files are passed to the function, the two published files
        will be returned. The criteria can be boolean or int (will return True
        booleans and the max integer).

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

        versionWeight takes a version string for
        a CMIP xml and returns a numeric in which the larger
        the number, the more recent the version. Typically
        an int corresponding to the date (e.g., 20190829), but
        will give precedence to version numbers (e.g., v1 is
        returned as 100000000).
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
    """ cdate, publish, tpoints = getFileMeta(fn)

        getFileMeta takes a filename (fn) for a CMIP xml
        and returns:
            cdate:      creation date
            publish:    boolean if the underlying data is
                        the publish directories
            tpoints:    the number of timesteps in the dataset
    """
    fh = cdms2.open(fn)
    cdate = fh.creation_date
    # most dates are of form: 2012-02-13T00:40:33Z
    # some are: Thu Aug 11 22:49:09 EST 2011 - just make 20110101
    if cdate[0].isalpha():
        cdate = int(cdate.split(' ')[-1] + '0101')
    else:
        cdate = int(cdate.split('T')[0].replace('-', ''))
    # check if published
    if fh.directory.find('publish') > 0:
        publish = True
    else:
        publish = False
    tpoints = len(fh['time'])
    fh.close()
    return cdate, publish, tpoints


def trimModelList(files,
                  criteria=['tpoints', 'publish', 'cdate', 'ver'],
                  verbose=False):
    """ filesOut = trimModelList(files)

        trimModelList takes in a list of xml files and returns a list of xml
        files such that there is one xml file per model and realization.

        The returned files are priorized by a cascading criteria, which can be
        optionally specified. The default order is:
            tpoints:    prioritizes files with more time steps
            publish:    prioritizes files that have been published
            cdate:      prioritizes files that were created more recently
            ver:        prioritizes files based on version id

        The cascading criteria can be altered by specifying an optional
        argument, critera, with a list of the strings above (e.g.,
        criteria=['publish', 'tpoints', 'ver', 'cdate']).

        An additional optional argument is verbose (boolean), which by default
        is False.
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
        cdate, publish, tpoints = getFileMeta(fn)
        # collect all models and rips
        models.append(model)
        rips.append(rip)
        # store data in dictionary
        keyMap[fn] = {'model': model, 'rip': rip, 'ver': ver, 'cdate': cdate,
                      'publish': publish, 'tpoints': tpoints}
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
