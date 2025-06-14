class ResultStruct:
    def __init__(self, iID, iName, iDOB, iAddress,iPhone):
        self.id = iID
        self.name = iName
        self.dob = iDOB
        self.address = iAddress
        self.phone = iPhone
        self.totalMatch = 0
        self.stringForRegex = ""
        self.keywordMatches = {}
        self.cv_path = ""