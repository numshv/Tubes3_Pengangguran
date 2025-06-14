class ResultStruct:
    def __init__(self, iID, iFirstName, iLastName, iDOB, iAddress,iPhone):
        self.id = iID
        self.firstName = iFirstName
        self.lastName = iLastName
        self.dob = iDOB
        self.address = iAddress
        self.phone = iPhone
        self.totalMatch = 0
        self.stringForRegex = ""
        self.keywordMatches = {}
        self.cv_path = ""