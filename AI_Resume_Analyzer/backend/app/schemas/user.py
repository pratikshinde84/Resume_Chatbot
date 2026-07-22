from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    userId: str
    name: str
    email: EmailStr

class StartSessionRequest(UserBase):
    pass

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class UploadedPDFResponse(BaseModel):
    filename: str
    pages: int

    class Config:
        from_attributes = True

class DeletePDFRequest(BaseModel):
    userId: str
    filename: str

class DeleteAllPDFsRequest(BaseModel):
    userId: str

class AskRequest(BaseModel):
    userId: str
    question: str

class AskResponse(BaseModel):
    answer: str
