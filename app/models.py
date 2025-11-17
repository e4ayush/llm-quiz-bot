from pydantic import BaseModel, HttpUrl

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: HttpUrl  # This specifically checks if the string looks like a valid URL