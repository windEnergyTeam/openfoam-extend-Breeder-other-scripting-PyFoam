#  ICE Revision: $Id:$
"""Working with a directory of samples"""

from os import path,listdir
from PyFoam.Error import error
import math

from PyFoam.Basics.SpreadsheetData import SpreadsheetData

class SampleDirectory(object):
    """A directory of sampled times"""

    def __init__(self,case,dirName="samples"):
        """@param case: The case directory
        @param dirName: Name of the directory with the samples"""

        self.dir=path.join(case,dirName)
        self.times=[]

        for d in listdir(self.dir):
            if path.isdir(path.join(self.dir,d)):
                try:
                    v=float(d)
                    self.times.append(d)
                except ValueError,e:
                    pass

        self.times.sort(self.sorttimes)

    def __len__(self):
        return len(self.times)

    def __iter__(self):
        for t in self.times:
            yield SampleTime(self.dir,t)

    def __getitem__(self,time):
        if time in self:
            return SampleTime(self.dir,time)
        else:
            raise KeyError,time

    def __contains__(self,time):
        return time in self.times
    
    def sorttimes(self,x,y):
        """Sort function for the solution files"""
        if(float(x)==float(y)):
            return 0
        elif float(x)<float(y):
            return -1
        else:
            return 1

    def lines(self):
        """Returns all the found sample lines"""

        lines=[]
        
        for t in self:
            for l in t.lines:
                if l not in lines:
                    lines.append(l)
        lines.sort()

        return lines

    def values(self):
        """Returns all the found sampled values"""
        
        values=[]
        
        for t in self:
            for v in t.values:
                if v not in values:
                    values.append(v)
        values.sort()

        return values

    def getData(self,line=None,value=None,time=None,note=""):
        """Get Sample sets
        @param line: name of the line. All
        if unspecified
        @param value: name of the sampled value. All
        if unspecified
        @param time: times for which the samples are to be got. All
        if unspecified
        @param note: A short annotation (for plots)"""
        
        if line==None:
            line=self.lines()
        if value==None:
            value=self.values()
        if time==None:
            time=self.times
            
        sets=[]

        for t in time:
            for l in line:
                for v in value:
                    try:
                        d=self[t][(l,v)]
                        d.note=note
                        sets.append(d)
                    except KeyError:
                        pass
            
        return sets
    
class SampleTime(object):
    """A directory with one sampled time"""

    def __init__(self,sDir,time):
        """@param sDir: The sample-dir
        @param time: the timename"""

        self.dir=path.join(sDir,time)
        self.lines=[]
        self.values=[]
        
        for f in listdir(self.dir):
            nm=self.extractLine(f)
            vals=self.extractValues(f)
            if nm not in self.lines:
                self.lines.append(nm)
            for v in vals:
                if v not in self.values:
                    self.values.append(v)

        self.lines.sort()
        self.values.sort()

        self.cache={}
        
    def extractLine(self,fName):
        """Extract the name of the line from a filename"""
        return fName.split("_")[0]

    def extractValues(self,fName):
        """Extracts the names of the contained Values from a filename"""
        tmp=fName.split("_")[1:]
        tmp[-1]=tmp[-1].split(".")[0]
        
        return tmp                            

    def __getitem__(self,key):
        """Get the data for a value on a specific line
        @param key: A tuple with the line-name and the value-name
        @returns: A SampleData-object"""

        if key in self.cache:
            return self.cache[key]
        
        line,val=key
        if line not in self.lines or val not in self.values:
            raise KeyError,key

        fName=None

        for f in listdir(self.dir):
            if line==self.extractLine(f) and val in self.extractValues(f):
                fName=f
                break

        if fName==None:
            error("Can't find a file for the line",line,"and the value",val,"in the directory",self.dir)

        first=True
        col0=[]
        data=[]
        
        for l in open(path.join(self.dir,fName)).readlines():
            tmp=l.split()
            if first:
                first=False
                vector,index=self.determineIndex(fName,val,tmp)

            col0.append(float(tmp[0]))
            try:
                if vector:
                    data.append(tuple(map(float,tmp[index:index+3])))
                else:
                    data.append(float(tmp[index]))
            except IndexError:
                raise KeyError(key)

        self.cache[key]=SampleData(fName=path.join(self.dir,fName),
                                   name=val,
                                   index=index,
                                   col0=col0,
                                   data=data)

        return self.cache[key]
    
    def determineIndex(self,fName,vName,data):
        """Determines the index of the data from the filename and a dataset
        @param fName: name of the file
        @param vName: Name of the quantity
        @param data: A list with the data
        @returns: A tuple of a boolean (whether the data is supposed to be
        a vector or a scalar) and an integer (the index of the data set -
        or the first component of the vector"""

        vals=self.extractValues(fName)
        if len(vals)+1==len(data):
            vector=False
        elif len(vals)*3+1==len(data):
            vector=True
        else:
            error("The data in file",fName,"is neither vector nor scalar:",data)

        index=vals.index(vName)
        if vector:
            index=index*3+1
        else:
            index=index+1

        return vector,index

class SampleData(object):
    """Data from a sample-set"""

    def __init__(self,fName,name,index,col0,data,note=""):
        """@param fName: Name of the file
        @param name: Name of the value
        @param index: Index of the data in the file
        @param col0: Values that identify the data (the location)
        @param data: The actual data"""
        
        self.file=fName
        self.col0=col0
        self.data=data
        self.name=name
        self.index=index
        self.note=note
        
    def __repr__(self):
        if self.isVector():
            vect=" (vector)"
        else:
            vect=""
            
        return "SampleData of %s%s on %s at t=%s " % (self.name,vect,self.line(),self.time())

    def line(self):
        """Get the line of the sample"""
        return path.basename(self.file).split("_")[0]
    
    def time(self):
        """Get the time of the sample (as a string)"""
        return path.basename(path.dirname(self.file))
    
    def isVector(self):
        """Is this vector or scalar data?"""
        if type(self.data[0])==tuple:
            return True
        else:
            return False

    def range(self,component=None):
        """Range of the data"""
        data=self.component(component)
        
        return (min(data),max(data))

    def domain(self):
        """Range of the data domain"""
        return (min(self.col0),max(self.col0))
    
    def component(self,component=None):
        """Return the data as a number of single scalars.
        @param component: If None for vectors the absolute value is taken.
        else the number of the component"""

        if self.isVector():
            data=[]
            if component==None:
                for d in self.data:
                    data.append(math.sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]))
            else:
                if component<0 or component>=len(self.data[0]):
                    error("Requested component",component,"does not fit the size of the data",len(self.data[0]))
                for d in self.data:
                    data.append(d[component])                    
            return data
        else:
            return self.data

    def __call__(self):
        """Return the data as SpreadsheetData-object"""
        
        data=[]
        if self.isVector():
            for i,c in enumerate(self.col0):
                data.append([c]+list(self.data[i]))
        else:
            for i,c in enumerate(self.col0):
                data.append([c,self.data[i]])

        names=["col0"]
        if self.isVector():
            names+=[self.name+"_x",self.name+"_y",self.name+"_z"]
        else:
            names.append(self.name)

        return SpreadsheetData(data=data,
                               names=names,
                               title="%s_t=%s" % (self.line(),self.time()))

